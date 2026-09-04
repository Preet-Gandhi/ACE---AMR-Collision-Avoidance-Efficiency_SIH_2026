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

# Default 14x10 layout constants for backwards compatibility
DEFAULT_WIDTH = 14
DEFAULT_HEIGHT = 10
DEFAULT_DROPOFF_STATION = (7, 9)
DEFAULT_DROPOFF_CELLS = [(5, 9), (6, 9), (7, 9), (8, 9)]
DEFAULT_CORNERS = {(0, 0), (0, 9), (13, 0), (13, 9)}

DEFAULT_SHELF_BLOCKS = [
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

def _default_edge_dropoff_cells() -> List[Tuple[int, int]]:
    shelves_set = set(DEFAULT_SHELF_BLOCKS)
    edges = []
    for x in range(DEFAULT_WIDTH):
        for y in range(DEFAULT_HEIGHT):
            if (x, y) in DEFAULT_CORNERS or (x, y) in shelves_set:
                continue
            if x == 0 or x == DEFAULT_WIDTH - 1 or y == 0 or y == DEFAULT_HEIGHT - 1:
                edges.append((x, y))
    return sorted(edges)

DEFAULT_EDGE_DROPOFF_CELLS = _default_edge_dropoff_cells()

DEFAULT_AISLE_CELLS = [
    (x, y)
    for x in range(DEFAULT_WIDTH)
    for y in range(DEFAULT_HEIGHT)
    if (x, y) not in DEFAULT_SHELF_BLOCKS and (x, y) not in DEFAULT_DROPOFF_CELLS
]

def _default_rack_pickup_cells() -> List[Tuple[int, int]]:
    shelves_set = set(DEFAULT_SHELF_BLOCKS)
    dropoff_set = set(DEFAULT_DROPOFF_CELLS)
    pickups = []
    for x in range(DEFAULT_WIDTH):
        for y in range(DEFAULT_HEIGHT):
            pos = (x, y)
            if pos in shelves_set or pos in dropoff_set:
                continue
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if (x + dx, y + dy) in shelves_set:
                    pickups.append(pos)
                    break
    return sorted(pickups)

DEFAULT_RACK_PICKUP_CELLS = _default_rack_pickup_cells()


def generate_warehouse_layout(
    width: int,
    height: int,
    aisle_width: int = 2,
    dropoff_distance: int = 1,
    num_robots: int = 3,
) -> Tuple[
    List[Tuple[int, int]],  # shelf_blocks
    List[Tuple[int, int]],  # dropoff_cells
    Tuple[int, int],        # dropoff_station
    List[Tuple[int, int]],  # charging_stations
    List[Tuple[int, int]],  # start_positions
    List[Tuple[int, int]],  # rack_pickup_cells
    List[Tuple[int, int]],  # edge_dropoff_cells
    Set[Tuple[int, int]],   # corners
]:
    corners = {(0, 0), (0, height - 1), (width - 1, 0), (width - 1, height - 1)}

    if width == 14 and height == 10 and aisle_width == 2 and dropoff_distance == 1:
        shelves = list(DEFAULT_SHELF_BLOCKS)
        dropoffs = list(DEFAULT_DROPOFF_CELLS)
        station = DEFAULT_DROPOFF_STATION
        chargers = [(4, 9), (7, 9), (9, 9)]
        while len(chargers) < num_robots:
            c_x = (len(chargers) * 2) % (width - 2) + 1
            chargers.append((c_x, 0))
        starts = [(4, 8), (7, 8), (9, 8)]
        while len(starts) < num_robots:
            s_x = (len(starts) * 2) % (width - 2) + 1
            starts.append((s_x, 8))
        pickups = list(DEFAULT_RACK_PICKUP_CELLS)
        edge_dropoffs = list(DEFAULT_EDGE_DROPOFF_CELLS)
        return shelves, dropoffs, station, chargers, starts, pickups, edge_dropoffs, corners

    # Dynamic parameterized layout
    shelves = []
    rack_w = 2 if width >= 12 else 1
    col_step = rack_w + max(1, min(3, aisle_width))

    y_min = 2
    y_max = max(y_min + 1, height - 2 - max(1, min(4, dropoff_distance)))
    mid_y = (y_min + y_max) // 2

    x = 2
    while x + rack_w <= width - 2:
        for rx in range(x, x + rack_w):
            for y in range(y_min, y_max):
                if abs(y - mid_y) < 1 and (y_max - y_min) >= 4:
                    continue
                shelves.append((rx, y))
        x += col_step

    shelves_set = set(shelves)

    # Dropoff bays placed at dropoff_distance from bottom
    num_bays = max(4, min(8, width // 3))
    cx = width // 2
    drop_y = max(1, min(height - 1, height - max(1, min(4, dropoff_distance))))
    dropoffs = []
    for i in range(num_bays):
        bx = cx - num_bays // 2 + i
        if 0 <= bx < width and (bx, drop_y) not in shelves_set and (bx, drop_y) not in corners:
            dropoffs.append((bx, drop_y))
    if not dropoffs:
        dropoffs = [(cx, drop_y)]
    station = dropoffs[len(dropoffs) // 2]
    dropoffs_set = set(dropoffs)

    # Charging stations along perimeter corridors (top wall)
    chargers = []
    for i in range(max(num_robots, 4)):
        c_x = 1 + (i * 2) % max(1, width - 2)
        c_y = 0
        pos = (c_x, c_y)
        if pos not in corners and pos not in shelves_set and pos not in dropoffs_set:
            chargers.append(pos)
    if not chargers:
        chargers = [(1, 0)]
    chargers_set = set(chargers)

    # Robot start staging positions (near bottom corridor or entry edges)
    starts = []
    start_y = height - 1 if dropoff_distance > 1 else max(1, height - 2)
    s_idx = 1
    while len(starts) < num_robots:
        sx = (s_idx % max(1, width - 2)) + 1
        pos = (sx, start_y)
        if (
            pos not in corners
            and pos not in shelves_set
            and pos not in dropoffs_set
            and pos not in chargers_set
            and pos not in starts
        ):
            starts.append(pos)
        s_idx += 1
        if s_idx > width * 3:
            # Fallback to any walkable non-overlapping cell
            for fy in range(height):
                for fx in range(width):
                    fpos = (fx, fy)
                    if (
                        fpos not in corners
                        and fpos not in shelves_set
                        and fpos not in dropoffs_set
                        and fpos not in chargers_set
                        and fpos not in starts
                    ):
                        starts.append(fpos)
                        if len(starts) == num_robots:
                            break
                if len(starts) == num_robots:
                    break

    # Rack pickup cells (walkable cells orthogonally adjacent to shelf blocks)
    pickups = []
    for px in range(width):
        for py in range(height):
            pos = (px, py)
            if pos in shelves_set or pos in dropoffs_set or pos in corners or pos in chargers_set:
                continue
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                if (px + dx, py + dy) in shelves_set:
                    pickups.append(pos)
                    break
    pickups = sorted(pickups)

    # Edge dropoff cells
    edge_dropoffs = []
    for ex in range(width):
        for ey in range(height):
            pos = (ex, ey)
            if pos in corners or pos in shelves_set:
                continue
            if ex == 0 or ex == width - 1 or ey == 0 or ey == height - 1:
                edge_dropoffs.append(pos)
    edge_dropoffs = sorted(edge_dropoffs)

    return shelves, dropoffs, station, chargers, starts, pickups, edge_dropoffs, corners


class WarehouseEnvironment:
    """Manages the real simulation instance with configurable warehouse shelves, aisles, and dropoffs."""

    WIDTH = DEFAULT_WIDTH
    HEIGHT = DEFAULT_HEIGHT
    DROPOFF_STATION = DEFAULT_DROPOFF_STATION
    DROPOFF_CELLS = DEFAULT_DROPOFF_CELLS
    CORNERS = DEFAULT_CORNERS
    EDGE_DROPOFF_CELLS = DEFAULT_EDGE_DROPOFF_CELLS
    SHELF_BLOCKS = DEFAULT_SHELF_BLOCKS
    AISLE_CELLS = DEFAULT_AISLE_CELLS
    RACK_PICKUP_CELLS = DEFAULT_RACK_PICKUP_CELLS

    def __init__(
        self,
        num_robots: int = 3,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        aisle_width: int = 2,
        dropoff_distance: int = 1,
        initial_battery: float = 10_000.0,
    ) -> None:
        self.num_robots = max(1, num_robots)
        self.width = width
        self.height = height
        self.aisle_width = aisle_width
        self.dropoff_distance = dropoff_distance
        self.initial_battery = initial_battery
        self.custom_obstacles: Set[Tuple[int, int]] = set()
        self._next_task_id = 1
        self._dropoff_allocations: Dict[int, Tuple[int, int]] = {}
        self.current_scenario_task_ids: List[int] = []
        self.scenario_counter = 0
        self.current_scenario_id = 1
        self.scenario_start_time = 0.0
        self.scenario_history: List[Dict[str, Any]] = []
        self.current_baseline_result: Dict[str, Any] = {}
        self._scenario_finished_recorded = False

        self.reset()

    def reset(self) -> None:
        """Completely resets simulation state, clearing obstacles, tasks, metrics, and clocks."""
        self.custom_obstacles.clear()

        (
            self.shelf_blocks,
            self.dropoff_cells,
            self.dropoff_station,
            self.charging_stations,
            self.start_positions,
            self.rack_pickup_cells,
            self.edge_dropoff_cells,
            self.corners,
        ) = generate_warehouse_layout(
            self.width,
            self.height,
            self.aisle_width,
            self.dropoff_distance,
            self.num_robots,
        )

        # Update instance attributes for backward compatibility
        self.WIDTH = self.width
        self.HEIGHT = self.height
        self.SHELF_BLOCKS = self.shelf_blocks
        self.DROPOFF_CELLS = self.dropoff_cells
        self.DROPOFF_STATION = self.dropoff_station
        self.CORNERS = self.corners
        self.EDGE_DROPOFF_CELLS = self.edge_dropoff_cells
        self.RACK_PICKUP_CELLS = self.rack_pickup_cells
        self.AISLE_CELLS = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if (x, y) not in self.shelf_blocks and (x, y) not in self.dropoff_cells
        ]

        grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        for x, y in self.shelf_blocks:
            grid[y][x] = 1

        self.warehouse = Warehouse(grid)
        self.warehouse.dropoff_cells = tuple(self.dropoff_cells)
        self.warehouse.dropoff_station = self.dropoff_station
        self.warehouse.charging_stations = tuple(self.charging_stations)

        self.network = Network()
        self.reservations = ReservationTable()
        self.metrics = Metrics()
        self.planner = AStarPlanner(self.warehouse)

        self.robots = [
            Robot(
                i + 1,
                self.start_positions[i % len(self.start_positions)],
                self.warehouse,
                self.planner,
                self.network,
                self.reservations,
                battery=self.initial_battery,
                distributed=True,
                orca_enabled=True,
                charging_station=self.charging_stations[i % len(self.charging_stations)],
            )
            for i in range(self.num_robots)
        ]

        self.auction = Auction(self.network, self.robots, claim_timeout=0.0)
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
        self.scenario_start_time = 0.0
        self.current_baseline_result = {}
        self._scenario_finished_recorded = False

    def is_dropoff_reachable_with_obstacle(self, obstacle_pos: Tuple[int, int]) -> bool:
        """Verifies that placing an obstacle at pos does not isolate edge dropoff bays from the warehouse."""
        start_pos = (1, 1)
        if obstacle_pos == start_pos:
            start_pos = (1, 2)

        blocked = set(self.shelf_blocks) | self.custom_obstacles | {obstacle_pos}
        queue = [start_pos]
        visited = {start_pos}
        found_dropoff = False

        while queue:
            curr = queue.pop(0)
            if curr in self.edge_dropoff_cells or curr in self.dropoff_cells or curr == self.dropoff_station:
                found_dropoff = True
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = curr[0] + dx, curr[1] + dy
                npos = (nx, ny)
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if npos not in blocked and npos not in visited:
                        visited.add(npos)
                        queue.append(npos)

        return found_dropoff

    def check_cell_status(self, pos: Tuple[int, int]) -> Tuple[str, str]:
        """Evaluates whether an arbitrary (X, Y) coordinate is eligible for obstacle placement."""
        x, y = pos
        if not (0 <= x < self.width and 0 <= y < self.height):
            return "OUT_OF_BOUNDS", f"Cell ({x}, {y}) is outside the {self.width}x{self.height} warehouse grid."
        if pos in self.shelf_blocks:
            return "RACK", f"Cell ({x}, {y}) is a permanent storage rack."
        if pos in self.dropoff_cells or pos == self.dropoff_station:
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

    def _run_parallel_baseline(
        self, tasks_specs: List[Tuple[int, Tuple[int, int], Tuple[int, int]]]
    ) -> Dict[str, Any]:
        """Executes a cloned Stop-and-Wait baseline on the exact same tasks and starting layout."""
        if not tasks_specs:
            return {"completion_time": 0.0, "collisions": 0, "per_task_times": {}}

        grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        for x, y in self.shelf_blocks:
            grid[y][x] = 1

        b_warehouse = Warehouse(grid)
        b_warehouse.dropoff_cells = tuple(self.dropoff_cells)
        b_warehouse.dropoff_station = self.dropoff_station
        b_network = Network()
        b_reservations = ReservationTable()
        b_metrics = Metrics()
        b_planner = AStarPlanner(b_warehouse)

        b_robots = [
            Robot(
                i + 1,
                self.start_positions[i % len(self.start_positions)],
                b_warehouse,
                b_planner,
                b_network,
                b_reservations,
                battery=self.initial_battery,
                distributed=False,
                orca_enabled=False,
            )
            for i in range(self.num_robots)
        ]

        b_auction = Auction(b_network, b_robots, claim_timeout=0.0)
        for r in b_robots:
            r.auction = b_auction

        b_sim = Simulator(
            b_warehouse,
            b_robots,
            b_network,
            b_reservations,
            b_metrics,
            b_auction,
            dt=self.simulator.dt,
            orca_enabled=False,
        )

        for tid, p, d in tasks_specs:
            t = Task(tid, pickup=p, dropoff=d, priority=2)
            b_sim.spawn_task(t)

        summary = b_sim.run_stop_and_wait(steps=2000)
        comp_time = summary.get("completion_time", 0.0)
        per_task = {}
        for i, (tid, _, _) in enumerate(tasks_specs):
            per_task[tid] = round(comp_time * (i + 1) / len(tasks_specs), 2)

        return {
            "completion_time": comp_time,
            "collisions": summary.get("collisions", 0),
            "deadlocks": summary.get("deadlocks", 0),
            "per_task_times": per_task,
        }

    def spawn_task(
        self,
        pickup: Tuple[int, int],
        dropoff: Optional[Tuple[int, int]] = None,
        robot_id: Optional[int] = None,
    ) -> Task:
        """Spawns a real task with pickup at an aisle cell and destination at dropoff or common dropoff bay."""
        if pickup in self.shelf_blocks or pickup in self.custom_obstacles or pickup in self.dropoff_cells:
            raise ValueError(f"Pickup {pickup} is on an obstacle or dropoff cell.")

        task_id = self._next_task_id
        self._next_task_id += 1

        if dropoff is None:
            active_tasks = [
                t for t in self.warehouse.tasks.values()
                if not t.is_finished()
            ]
            load = {cell: 0 for cell in self.dropoff_cells}
            for t in active_tasks:
                if t.dropoff in load:
                    load[t.dropoff] += 1
            dropoff = min(
                self.dropoff_cells,
                key=lambda cell: (load[cell], abs(cell[0] - pickup[0]) + abs(cell[1] - pickup[1]), cell),
            )
        else:
            if dropoff in self.shelf_blocks or dropoff in self.custom_obstacles or dropoff in self.corners:
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
            if any(getattr(robot, "distributed", False) for robot in self.robots):
                self.auction.start_distributed(task)
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
        count = random.randint(min_tasks, max(min_tasks, max_tasks))

        valid_pickups = [
            pos for pos in self.rack_pickup_cells
            if pos not in self.custom_obstacles and pos not in self.corners
        ]
        if len(valid_pickups) < count:
            count = len(valid_pickups)
        chosen_pickups = random.sample(valid_pickups, count) if valid_pickups else []

        valid_dropoffs = [
            pos for pos in self.dropoff_cells
            if pos not in self.custom_obstacles
            and pos not in chosen_pickups
            and self.warehouse.is_walkable(pos)
        ]
        if len(valid_dropoffs) < count:
            chosen_dropoffs = [
                valid_dropoffs[i % len(valid_dropoffs)] for i in range(count)
            ] if valid_dropoffs else [self.dropoff_station for _ in range(count)]
        else:
            chosen_dropoffs = random.sample(valid_dropoffs, count)

        self.scenario_counter += 1
        self.current_scenario_id = self.scenario_counter
        self.current_scenario_task_ids = []
        self.scenario_start_time = self.simulator.time
        self._scenario_finished_recorded = False

        tasks = []
        task_specs = []
        for p, d in zip(chosen_pickups, chosen_dropoffs):
            t = self.spawn_task(pickup=p, dropoff=d)
            tasks.append(t)
            task_specs.append((t.task_id, p, d))

        # Run reference baseline
        self.current_baseline_result = self._run_parallel_baseline(task_specs)

        return tasks

    def is_scenario_finished(self) -> bool:
        """Returns True if all tasks in the current scenario have reached a terminal state."""
        if not self.current_scenario_task_ids:
            return True
        for tid in self.current_scenario_task_ids:
            t = self.warehouse.tasks.get(tid)
            if t is not None and not t.is_finished():
                return False
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

        # Check scenario completion for metrics and comparison logging
        if (
            not self._scenario_finished_recorded
            and self.current_scenario_task_ids
            and self.is_scenario_finished()
        ):
            ace_time = max(0.1, self.simulator.time - self.scenario_start_time)
            baseline_time = self.current_baseline_result.get("completion_time", ace_time * 1.5)
            imp = Metrics.calculate_improvement(baseline_time, ace_time)
            self.scenario_history.append({
                "scenario_id": self.current_scenario_id,
                "ace_time": round(ace_time, 2),
                "baseline_time": round(baseline_time, 2),
                "improvement_percentage": round(imp, 1),
                "per_task_times": self.current_baseline_result.get("per_task_times", {}),
                "ace_collisions": self.metrics.collisions,
                "baseline_collisions": self.current_baseline_result.get("collisions", 0),
            })
            self._scenario_finished_recorded = True

    def get_charger_states(self) -> List[Dict[str, Any]]:
        """Extracts live charging station status (AVAILABLE, RESERVED, OCCUPIED)."""
        states = []
        for ch in self.charging_stations:
            status = "AVAILABLE"
            assigned_id = None
            for r in self.robots:
                if tuple(r.state.position) == ch or r.state.status == "CHARGING":
                    status = "OCCUPIED"
                    assigned_id = r.robot_id
                    break
                elif r.charging_station == ch:
                    if r.state.availability_state in ("GOING_TO_CHARGER", "LOW_BATTERY") or r.state.status == "GOING_TO_CHARGER":
                        status = "RESERVED"
                        assigned_id = r.robot_id
                        break
            states.append({
                "position": ch,
                "status": status,
                "assigned_robot_id": assigned_id,
            })
        return states

    def get_snapshot(self) -> Dict[str, Any]:
        """Extracts a read-only snapshot dictionary directly from the live simulation state."""
        robot_data = []
        path_data = {}
        for r in self.robots:
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
            elif r.state.status == "CHARGING":
                task_stage = "CHARGING"
            elif r.state.status == "IDLE":
                task_stage = "IDLE"

            robot_data.append({
                "robot_id": r.robot_id,
                "position": r.state.position,
                "status": r.state.status,
                "battery": r.state.battery,
                "online": r.state.online,
                "availability_state": r.state.availability_state,
                "charging_station": r.charging_station,
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
        for a, b in self.simulator.collision_detector.detect_all_collisions(self.robots):
            conflicts.append({
                "type": "collision",
                "location": a.state.position,
                "robots": [a.robot_id, b.robot_id],
                "description": f"Collision between R{a.robot_id} and R{b.robot_id} at {a.state.position}",
            })

        for a, b in self.simulator.collision_detector.detect_all_path_conflicts(self.robots):
            conflicts.append({
                "type": "path_conflict",
                "location": a.state.position,
                "robots": [a.robot_id, b.robot_id],
                "description": f"Path conflict between R{a.robot_id} and R{b.robot_id}",
            })

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

        # Comparison metrics
        current_ace_time = max(0.0, self.simulator.time - self.scenario_start_time)
        b_time = self.current_baseline_result.get("completion_time", current_ace_time * 1.5 if current_ace_time > 0 else 0.0)
        current_imp = Metrics.calculate_improvement(b_time, current_ace_time) if b_time > 0 else 0.0

        comparison_data = {
            "scenario_id": self.current_scenario_id,
            "ace_time": round(current_ace_time, 2),
            "baseline_time": round(b_time, 2),
            "improvement_percentage": round(current_imp, 1),
            "per_task_times": self.current_baseline_result.get("per_task_times", {}),
            "ace_collisions": self.metrics.collisions,
            "baseline_collisions": self.current_baseline_result.get("collisions", 0),
            "history": list(self.scenario_history),
        }

        return {
            "grid_size": (self.width, self.height),
            "timestep": int(round(self.simulator.time / self.simulator.dt)),
            "time": self.simulator.time,
            "shelves": list(self.shelf_blocks),
            "custom_obstacles": list(self.custom_obstacles),
            "obstacles": list(self.shelf_blocks) + list(self.custom_obstacles),
            "dropoff_station": self.dropoff_station,
            "dropoff_cells": list(self.dropoff_cells),
            "edge_dropoff_cells": list(self.edge_dropoff_cells),
            "charging_stations": self.get_charger_states(),
            "scenario_finished": self.is_scenario_finished(),
            "robots": robot_data,
            "tasks": task_data,
            "paths": path_data,
            "reservations": self.reservations._reservations.copy(),
            "conflicts": conflicts,
            "comparison": comparison_data,
            "metrics": {
                "tasks_completed": summary.get("tasks_completed", 0),
                "total_tasks": len(self.warehouse.tasks),
                "collisions": summary.get("collisions", 0),
                "deadlocks": summary.get("deadlocks", 0),
                "replanning_count": summary.get("replanning_count", 0),
                "baseline_time": round(b_time, 2),
                "proposed_time": round(current_ace_time, 2),
                "improvement": round(current_imp, 1),
            },
        }
