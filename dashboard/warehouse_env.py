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
CORNERS = {(0, 0), (0, HEIGHT - 1), (WIDTH - 1, 0), (WIDTH - 1, HEIGHT - 1)}

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

# Valid perimeter edge-area dropoff positions (perimeter excluding corners and rack overlaps)
def _find_edge_dropoff_cells() -> List[Tuple[int, int]]:
    shelves_set = set(SHELF_BLOCKS)
    edges = []
    for x in range(WIDTH):
        for y in range(HEIGHT):
            if (x, y) in CORNERS or (x, y) in shelves_set:
                continue
            if x == 0 or x == WIDTH - 1 or y == 0 or y == HEIGHT - 1:
                edges.append((x, y))
    return sorted(edges)

EDGE_DROPOFF_CELLS = _find_edge_dropoff_cells()

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
    CORNERS = CORNERS
    EDGE_DROPOFF_CELLS = EDGE_DROPOFF_CELLS
    SHELF_BLOCKS = SHELF_BLOCKS
    AISLE_CELLS = AISLE_CELLS
    RACK_PICKUP_CELLS = RACK_PICKUP_CELLS

    def __init__(self, num_robots: int = 3) -> None:
        self.num_robots = num_robots
        self.custom_obstacles: Set[Tuple[int, int]] = set()
        self._next_task_id = 1
        self._dropoff_allocations: Dict[int, Tuple[int, int]] = {}
        self.current_scenario_task_ids: List[int] = []
        self.reset()

    def reset(self) -> None:
        """Completely resets simulation state, clearing obstacles, tasks, metrics, and clocks."""
        self.custom_obstacles.clear()
        grid = [[0 for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]
        for x, y in self.SHELF_BLOCKS:
            grid[y][x] = 1

        self.warehouse = Warehouse(grid)
        # Expose the physical perimeter delivery-bay capacity to the planner.
        self.warehouse.dropoff_cells = tuple(self.EDGE_DROPOFF_CELLS)
        self.warehouse.dropoff_station = self.DROPOFF_STATION
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
                distributed=True,
                orca_enabled=True,
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
            orca_enabled=True,
        )
        self._next_task_id = 1
        self._dropoff_allocations = {}
        self.current_scenario_task_ids = []

    def is_dropoff_reachable_with_obstacle(self, obstacle_pos: Tuple[int, int]) -> bool:
        """Verifies that placing an obstacle at pos does not isolate edge dropoff bays from the warehouse."""
        start_pos = (1, 1)
        if obstacle_pos == start_pos:
            start_pos = (1, 2)

        blocked = set(self.SHELF_BLOCKS) | self.custom_obstacles | {obstacle_pos}
        queue = [start_pos]
        visited = {start_pos}
        found_dropoff = False

        while queue:
            curr = queue.pop(0)
            if curr in self.EDGE_DROPOFF_CELLS or curr == self.DROPOFF_STATION:
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
        if any(r.state.position == pos for r in self.robots):
            return "OCCUPIED_BY_ROBOT", f"Cell ({x}, {y}) is currently occupied by an active AMR."
        if not self.is_dropoff_reachable_with_obstacle(pos):
            return "WOULD_BLOCK_DROPOFF", f"Placing an obstacle at ({x}, {y}) would isolate dropoff bays."
        return "AVAILABLE", f"Cell ({x}, {y}) is available for obstacle placement."

    def add_custom_obstacle(self, pos: Tuple[int, int]) -> Tuple[bool, str]:
        """Places a dynamic custom obstacle on any valid non-rack cell, triggering real replanning."""
        status, message = self.check_cell_status(pos)
        if status != "AVAILABLE":
            return False, message

        self.custom_obstacles.add(pos)
        self.simulator.spawn_obstacle(pos)
        for r in self.robots:
            r.handle_obstacle(pos, announce=False)
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

    def spawn_task(
        self,
        pickup: Tuple[int, int],
        dropoff: Optional[Tuple[int, int]] = None,
        robot_id: Optional[int] = None,
    ) -> Task:
        """Spawns a real task with pickup at an aisle cell and destination at dropoff or common dropoff bay."""
        if pickup in self.SHELF_BLOCKS or pickup in self.custom_obstacles or pickup in self.DROPOFF_CELLS:
            raise ValueError(f"Pickup {pickup} is on an obstacle or dropoff cell.")

        task_id = self._next_task_id
        self._next_task_id += 1

        if dropoff is None:
            # Allocate the least-loaded bay slot from DROPOFF_CELLS
            active_tasks = [
                t for t in self.warehouse.tasks.values()
                if not t.is_finished()
            ]
            load = {cell: 0 for cell in self.DROPOFF_CELLS}
            for t in active_tasks:
                if t.dropoff in load:
                    load[t.dropoff] += 1
            dropoff = min(
                self.DROPOFF_CELLS,
                key=lambda cell: (load[cell], abs(cell[0] - pickup[0]) + abs(cell[1] - pickup[1]), cell),
            )
        else:
            if dropoff in self.SHELF_BLOCKS or dropoff in self.custom_obstacles or dropoff in self.CORNERS:
                raise ValueError(f"Dropoff {dropoff} is on an obstacle, shelf, or corner.")

        task = Task(task_id, pickup=pickup, dropoff=dropoff, priority=2)
        self.warehouse.add_task(task)
        self._dropoff_allocations[task_id] = dropoff
        self.current_scenario_task_ids.append(task_id)

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

    def generate_scenario(
        self, min_tasks: int = 1, max_tasks: Optional[int] = None
    ) -> List[Task]:
        """Generates a randomized multi-robot delivery scenario with distinct edge-area dropoffs."""
        if max_tasks is None:
            max_tasks = min(3, self.num_robots)
        count = random.randint(min_tasks, max_tasks)

        # 1. Candidate pickup locations (rack-adjacent aisle cells)
        valid_pickups = [
            pos for pos in self.RACK_PICKUP_CELLS
            if pos not in self.custom_obstacles and pos not in self.CORNERS
        ]
        if len(valid_pickups) < count:
            count = len(valid_pickups)
        chosen_pickups = random.sample(valid_pickups, count)

        # 2. Candidate delivery-bay slots. Keep generated scenarios aligned
        # with the physical dropoff station instead of sending robots to
        # arbitrary perimeter cells (which produced the bad-looking long
        # routes visible in the dashboard).
        valid_dropoffs = [
            pos for pos in self.DROPOFF_CELLS
            if pos not in self.custom_obstacles
            and pos not in chosen_pickups
            and self.warehouse.is_walkable(pos)
        ]
        if len(valid_dropoffs) < count:
            count = len(valid_dropoffs)
        chosen_dropoffs = random.sample(valid_dropoffs, count)

        self.current_scenario_task_ids = []
        tasks = []
        for p, d in zip(chosen_pickups, chosen_dropoffs):
            t = self.spawn_task(pickup=p, dropoff=d)
            tasks.append(t)

        return tasks

    def is_scenario_finished(self) -> bool:
        """Returns True if all tasks in the current scenario have reached a terminal state."""
        if not self.current_scenario_task_ids:
            return True
        for tid in self.current_scenario_task_ids:
            t = self.warehouse.tasks.get(tid)
            if t is not None and not t.is_finished():
                return False
        # Ensure robots assigned to this scenario have cleared their task
        for r in self.robots:
            if r.state.current_task_id in self.current_scenario_task_ids:
                return False
        return True

    def randomize_pickups(self, count: int = 3) -> List[Task]:
        """Picks random rack-facing aisle positions and routes them using the real auction and planner."""
        return self.generate_scenario(min_tasks=count, max_tasks=count)

    def step(self) -> None:
        """Advances the real simulation clock by one step."""
        self.simulator.step()
        for task_id, cell in list(self._dropoff_allocations.items()):
            task = self.warehouse.tasks.get(task_id)
            if task is not None and task.is_finished():
                del self._dropoff_allocations[task_id]

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
            has_package = bool(r.state.carrying_package)
            task_stage = "IDLE"

            if task is not None:
                if has_package and r.state.position == task.dropoff and not remaining_wps:
                    task_stage = "DELIVERED"
                elif has_package:
                    task_stage = "TRANSPORTING"
                elif r.state.position == task.pickup:
                    task_stage = "AT_PICKUP"
                else:
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
            assigned_r = next((r for r in self.robots if r.robot_id == t.assigned_robot_id), None)
            is_picked_up = bool(
                assigned_r
                and assigned_r.state.carrying_package
                and assigned_r.state.current_task_id == t.task_id
            )
            task_data.append({
                "task_id": t.task_id,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "pickup": t.pickup,
                "dropoff": t.dropoff,
                "assigned_robot_id": t.assigned_robot_id,
                "is_picked_up": is_picked_up,
                "is_finished": t.is_finished(),
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
            "edge_dropoff_cells": list(self.EDGE_DROPOFF_CELLS),
            "scenario_finished": self.is_scenario_finished(),
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
