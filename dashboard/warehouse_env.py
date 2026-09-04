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

# Valid aisle positions
AISLE_CELLS = [
    (x, y)
    for x in range(WIDTH)
    for y in range(HEIGHT)
    if (x, y) not in SHELF_BLOCKS and (x, y) not in DROPOFF_CELLS
]

# Rack-facing aisle pickup locations (walkable cells orthogonally adjacent to storage racks)
def _find_rack_pickup_cells() -> List[Tuple[int, int]]:
    shelves_set = set(SHELF_BLOCKS)
    dropoff_set = set(DROPOFF_CELLS)
    pickups = []
    for x in range(WIDTH):
        for y in range(HEIGHT):
            pos = (x, y)
            if pos in shelves_set or pos in dropoff_set:
                continue
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if (x + dx, y + dy) in shelves_set:
                    pickups.append(pos)
                    break
    return sorted(pickups)

RACK_PICKUP_CELLS = _find_rack_pickup_cells()


class WarehouseEnvironment:
    """Manages the real simulation instance with warehouse shelves, aisles, and common dropoff."""

    WIDTH = WIDTH
    HEIGHT = HEIGHT
    DROPOFF_STATION = DROPOFF_STATION
    DROPOFF_CELLS = DROPOFF_CELLS
    SHELF_BLOCKS = SHELF_BLOCKS
    AISLE_CELLS = AISLE_CELLS
    RACK_PICKUP_CELLS = RACK_PICKUP_CELLS

    def __init__(self, num_robots: int = 3) -> None:
        self.num_robots = num_robots
        self.custom_obstacles: Set[Tuple[int, int]] = set()
        self._next_task_id = 1
        self.reset()

    def reset(self) -> None:
        """Completely resets simulation state, clearing obstacles, tasks, metrics, and clocks."""
        self.custom_obstacles.clear()
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
        self._next_task_id = 1

    def is_dropoff_reachable_with_obstacle(self, obstacle_pos: Tuple[int, int]) -> bool:
        """Verifies that placing an obstacle at pos does not disconnect the common dropoff from the warehouse."""
        start_pos = (0, 0)
        if obstacle_pos == start_pos:
            start_pos = (0, 1)

        blocked = set(self.SHELF_BLOCKS) | self.custom_obstacles | {obstacle_pos}
        queue = [start_pos]
        visited = {start_pos}
        found_dropoff = False

        while queue:
            curr = queue.pop(0)
            if curr == self.DROPOFF_STATION or curr in self.DROPOFF_CELLS:
                found_dropoff = True
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = curr[0] + dx, curr[1] + dy
                npos = (nx, ny)
                if 0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT:
                    if npos not in blocked and npos not in visited:
                        visited.add(npos)
                        queue.append(npos)

        return found_dropoff

    def check_cell_status(self, pos: Tuple[int, int]) -> Tuple[str, str]:
        """Evaluates whether an arbitrary (X, Y) coordinate is eligible for obstacle placement."""
        x, y = pos
        if not (0 <= x < self.WIDTH and 0 <= y < self.HEIGHT):
            return "OUT_OF_BOUNDS", f"Cell ({x}, {y}) is outside the {self.WIDTH}x{self.HEIGHT} warehouse grid."
        if pos in self.SHELF_BLOCKS:
            return "RACK", f"Cell ({x}, {y}) is a permanent storage rack."
        if pos in self.DROPOFF_CELLS or pos == self.DROPOFF_STATION:
            return "DROPOFF", f"Cell ({x}, {y}) is part of the common dropoff station."
        if pos in self.custom_obstacles:
            return "EXISTING_OBSTACLE", f"Cell ({x}, {y}) already has a custom obstacle."
        if not self.is_dropoff_reachable_with_obstacle(pos):
            return "WOULD_BLOCK_DROPOFF", f"Placing an obstacle at ({x}, {y}) would isolate the dropoff station."
        return "AVAILABLE", f"Cell ({x}, {y}) is available for obstacle placement."

    def add_custom_obstacle(self, pos: Tuple[int, int]) -> Tuple[bool, str]:
        """Places a dynamic custom obstacle on any valid non-rack cell, triggering real replanning."""
        status, message = self.check_cell_status(pos)
        if status != "AVAILABLE":
            return False, message

        self.custom_obstacles.add(pos)
        self.simulator.spawn_obstacle(pos)
        for r in self.robots:
            r.handle_obstacle(pos, announce=True)
            r.update()
        return True, f"Obstacle placed at ({pos[0]}, {pos[1]}). Real replan triggered."

    def remove_custom_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Removes a dynamic obstacle from the warehouse."""
        if pos in self.custom_obstacles:
            self.custom_obstacles.remove(pos)
            self.simulator.remove_obstacle(pos)
            for r in self.robots:
                r.update()
            return True
        return False

    def spawn_task(self, pickup: Tuple[int, int], robot_id: Optional[int] = None) -> Task:
        """Spawns a real task with pickup at an aisle cell and destination at the common dropoff."""
        if pickup in self.SHELF_BLOCKS or pickup in self.custom_obstacles or pickup in self.DROPOFF_CELLS:
            raise ValueError(f"Pickup {pickup} is on an obstacle or dropoff cell.")

        task_id = self._next_task_id
        self._next_task_id += 1

        task = Task(task_id, pickup=pickup, dropoff=self.DROPOFF_STATION, priority=2)
        self.warehouse.add_task(task)

        if robot_id is not None:
            target_robot = next((r for r in self.robots if r.robot_id == robot_id), None)
            if target_robot:
                task.assign(target_robot.robot_id)
                target_robot.accept_task(task)
                target_robot.update()
        else:
            self.auction.run_auction(task, verbose=False)
            for r in self.robots:
                r.update()

        return task

    def randomize_pickups(self, count: int = 3) -> List[Task]:
        """Picks random rack-facing aisle positions and routes them using the real auction and planner."""
        valid_candidates = [
            pos for pos in self.RACK_PICKUP_CELLS
            if pos not in self.custom_obstacles and pos != self.DROPOFF_STATION and pos not in self.DROPOFF_CELLS
        ]
        chosen = random.sample(valid_candidates, min(count, len(valid_candidates)))
        tasks = []
        for p in chosen:
            tasks.append(self.spawn_task(p))
        return tasks

    def step(self) -> None:
        """Advances the real simulation clock by one step."""
        self.simulator.step()

    def get_snapshot(self) -> Dict[str, Any]:
        """Extracts a read-only snapshot dictionary directly from the live simulation state."""
        robot_data = []
        path_data = {}
        for r in self.robots:
            # Real planned path starts at current robot position followed by remaining waypoints
            remaining_wps = list(r.state.path[r.state.path_index:])
            full_path = [r.state.position] + remaining_wps

            task_id = r.state.current_task_id
            task = self.warehouse.tasks.get(task_id) if task_id is not None else None
            has_package = False
            task_stage = "IDLE"

            if task is not None:
                if r.state.position == task.pickup:
                    has_package = True
                    task_stage = "AT_PICKUP"
                elif remaining_wps and remaining_wps[-1] == task.dropoff:
                    has_package = True
                    task_stage = "TRANSPORTING"
                elif r.state.position == task.dropoff and not remaining_wps:
                    has_package = False
                    task_stage = "DELIVERED"
                else:
                    has_package = False
                    task_stage = "GOING_TO_PICKUP"
            elif r.state.status == "WAITING":
                task_stage = "WAITING"
            elif r.state.status == "IDLE":
                task_stage = "IDLE"

            robot_data.append({
                "robot_id": r.robot_id,
                "position": r.state.position,
                "status": r.state.status,
                "current_task_id": r.state.current_task_id,
                "path": full_path,
                "has_package": has_package,
                "task_stage": task_stage,
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
        # 1. Collision detector physical collisions
        for a, b in self.simulator.collision_detector.detect_all_collisions(self.robots):
            conflicts.append({
                "type": "collision",
                "location": a.state.position,
                "robots": [a.robot_id, b.robot_id],
                "description": f"Collision between R{a.robot_id} and R{b.robot_id} at {a.state.position}",
            })

        # 2. Collision detector predicted path conflicts
        for a, b in self.simulator.collision_detector.detect_all_path_conflicts(self.robots):
            conflicts.append({
                "type": "path_conflict",
                "location": a.state.position,
                "robots": [a.robot_id, b.robot_id],
                "description": f"Path conflict between R{a.robot_id} and R{b.robot_id}",
            })

        # 3. Deadlock detector
        dl = self.simulator.deadlock_detector.detect_deadlocks(self.robots)
        if dl.get("detected"):
            for r_id in dl.get("robots", []):
                r_obj = next((r for r in self.robots if r.robot_id == r_id), None)
                loc = r_obj.state.position if r_obj else None
                conflicts.append({
                    "type": "deadlock",
                    "location": loc,
                    "robots": dl.get("robots", []),
                    "description": f"Deadlock cycle involving robots {dl.get('robots')}",
                })

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
