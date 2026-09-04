from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from auction.auction import Auction
from auction.task import Task
from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.metrics import Metrics
from simulation.simulator import Simulator
from simulation.warehouse import Warehouse


WIDTH = 14
HEIGHT = 10
DROPOFF_STATION = (7, 9)
DROPOFF_CELLS = [(5, 9), (6, 9), (7, 9), (8, 9)]

# Shelf rack obstacles defining aisles
SHELF_BLOCKS = [
    # Left rack cluster
    (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3),
    (2, 5), (2, 6), (2, 7), (3, 5), (3, 6), (3, 7),
    # Center rack cluster
    (6, 1), (6, 2), (6, 3), (7, 1), (7, 2), (7, 3),
    (6, 5), (6, 6), (6, 7), (7, 5), (7, 6), (7, 7),
    # Right rack cluster
    (10, 1), (10, 2), (10, 3), (11, 1), (11, 2), (11, 3),
    (10, 5), (10, 6), (10, 7), (11, 5), (11, 6), (11, 7),
]

# Valid aisle positions where pickups can occur
AISLE_CELLS = [
    (x, y)
    for x in range(WIDTH)
    for y in range(HEIGHT - 1)  # exclude bottom dropoff row
    if (x, y) not in SHELF_BLOCKS
]


class WarehouseEnvironment:
    """Manages the real simulation instance with warehouse shelves, aisles, and common dropoff."""

    WIDTH = WIDTH
    HEIGHT = HEIGHT
    DROPOFF_STATION = DROPOFF_STATION
    DROPOFF_CELLS = DROPOFF_CELLS
    SHELF_BLOCKS = SHELF_BLOCKS
    AISLE_CELLS = AISLE_CELLS

    def __init__(self, num_robots: int = 3) -> None:
        self.num_robots = num_robots
        self.custom_obstacles: Set[Tuple[int, int]] = set()
        self._next_task_id = 1
        self.reset()

    def reset(self) -> None:
        grid = [[0 for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]
        for x, y in self.SHELF_BLOCKS:
            grid[y][x] = 1

        self.warehouse = Warehouse(grid)
        self.network = Network()
        self.reservations = ReservationTable()
        self.metrics = Metrics()
        self.planner = AStarPlanner(self.warehouse)

        # Robots start at staging area above dropoff station
        start_positions = [(4, 8), (7, 8), (9, 8)]
        self.robots = [
            Robot(
                i + 1,
                start_positions[i % len(start_positions)],
                self.warehouse,
                self.planner,
                self.network,
                self.reservations,
                battery=10_000.0,
            )
            for i in range(self.num_robots)
        ]

        self.auction = Auction(self.network, self.robots)
        for r in self.robots:
            r.auction = self.auction
        self.simulator = Simulator(
            self.warehouse,
            self.robots,
            self.network,
            self.reservations,
            self.metrics,
            self.auction,
            dt=0.1,
        )

        # Re-apply any custom obstacles
        for obs in self.custom_obstacles:
            self.simulator.spawn_obstacle(obs)

        self._next_task_id = 1

    def spawn_task(self, pickup: Tuple[int, int], robot_id: Optional[int] = None) -> Task:
        """Spawns a real task with pickup at an aisle cell and destination at the common dropoff."""
        if pickup in self.SHELF_BLOCKS or pickup in self.custom_obstacles:
            raise ValueError(f"Pickup {pickup} is on an obstacle cell.")

        task_id = self._next_task_id
        self._next_task_id += 1

        task = Task(task_id, pickup=pickup, dropoff=self.DROPOFF_STATION, priority=2)
        self.warehouse.add_task(task)

        if robot_id is not None:
            # Assign explicitly to a specific robot
            target_robot = next((r for r in self.robots if r.robot_id == robot_id), None)
            if target_robot:
                task.assign(target_robot.robot_id)
                target_robot.accept_task(task)
                target_robot.update()
        else:
            # Use real auction assignment
            self.auction.run_auction(task, verbose=False)
            for r in self.robots:
                r.update()

        return task

    def randomize_pickups(self, count: int = 3) -> List[Task]:
        """Picks random valid aisle positions and routes them using the real auction and planner."""
        valid_candidates = [
            pos for pos in self.AISLE_CELLS
            if pos not in self.custom_obstacles and pos != self.DROPOFF_STATION
        ]
        chosen = random.sample(valid_candidates, min(count, len(valid_candidates)))
        tasks = []
        for p in chosen:
            tasks.append(self.spawn_task(p))
        return tasks

    def add_custom_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Places a dynamic custom obstacle in the simulation, triggering real replanning."""
        if pos in self.SHELF_BLOCKS or pos in self.DROPOFF_CELLS or pos == self.DROPOFF_STATION:
            return False
        if pos in self.custom_obstacles:
            return False

        self.custom_obstacles.add(pos)
        self.simulator.spawn_obstacle(pos)
        for r in self.robots:
            r.handle_obstacle(pos, announce=True)
            r.update()
        return True

    def remove_custom_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Removes a dynamic obstacle from the warehouse."""
        if pos in self.custom_obstacles:
            self.custom_obstacles.remove(pos)
            self.simulator.remove_obstacle(pos)
            for r in self.robots:
                r.update()
            return True
        return False

    def step(self) -> None:
        """Advances the real simulation clock by one step."""
        self.simulator.step()

    def get_snapshot(self) -> Dict[str, Any]:
        """Extracts a read-only snapshot dictionary directly from the live simulation state."""
        robot_data = []
        path_data = {}
        for r in self.robots:
            # Full path includes current position plus remaining waypoints
            full_path = [r.state.position] + list(r.state.path)
            robot_data.append({
                "robot_id": r.robot_id,
                "position": r.state.position,
                "status": r.state.status,
                "current_task_id": r.state.current_task_id,
                "path": full_path,
            })
            path_data[r.robot_id] = full_path

        task_data = []
        for t in self.warehouse.tasks.values():
            task_data.append({
                "task_id": t.task_id,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "pickup": t.pickup,
                "dropoff": t.dropoff,
                "assigned_robot_id": t.assigned_robot_id,
            })

        conflicts = []
        for a, b in self.simulator.collision_detector.detect_all_collisions(self.robots):
            conflicts.append(("vertex", a.state.position, self.simulator.time, b.robot_id))

        summary = self.metrics.get_summary()

        return {
            "grid_size": (self.WIDTH, self.HEIGHT),
            "timestep": int(round(self.simulator.time / self.simulator.dt)),
            "time": self.simulator.time,
            "shelves": list(self.SHELF_BLOCKS),
            "custom_obstacles": list(self.custom_obstacles),
            "obstacles": list(self.SHELF_BLOCKS) + list(self.custom_obstacles),
            "dropoff_station": self.DROPOFF_STATION,
            "dropoff_cells": list(self.DROPOFF_CELLS),
            "robots": robot_data,
            "tasks": task_data,
            "paths": path_data,
            "reservations": self.reservations._reservations.copy(),
            "conflicts": conflicts,
            "metrics": {
                "tasks_completed": summary.get("tasks_completed", 0),
                "total_tasks": len(self.warehouse.tasks),
                "collisions": summary.get("collisions", 0),
                "deadlocks": summary.get("deadlocks", 0),
                "replanning_count": summary.get("replanning_count", 0),
            },
        }
