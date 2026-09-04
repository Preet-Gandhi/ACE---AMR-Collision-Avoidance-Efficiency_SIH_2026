from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class RobotView:
    robot_id: Any
    position: Tuple[int, int]
    status: str = "UNKNOWN"
    battery: Optional[float] = None
    current_task_id: Optional[Any] = None
    path: Tuple[Tuple[int, int], ...] = ()
    has_package: bool = False
    task_stage: str = "IDLE"


@dataclass(frozen=True)
class TaskView:
    task_id: Any
    status: str = "PENDING"
    priority: int = 0
    pickup: Optional[Tuple[int, int]] = None
    dropoff: Optional[Tuple[int, int]] = None
    assigned_robot_id: Optional[Any] = None
    is_picked_up: bool = False
    is_finished: bool = False


@dataclass(frozen=True)
class ReservationView:
    robot_id: Any
    position: Tuple[int, int]
    timestep: Optional[int] = None


@dataclass(frozen=True)
class ConflictView:
    conflict_type: str
    description: str
    location: Optional[Tuple[int, int]] = None
    robots: Tuple[Any, ...] = ()


@dataclass(frozen=True)
class MetricView:
    collisions: int = 0
    deadlocks: int = 0
    tasks_completed: int = 0
    total_distance: float = 0.0
    waiting_time: float = 0.0
    replanning_count: int = 0
    completion_time: float = 0.0
    total_tasks: Optional[int] = None
    completion_percentage: Optional[float] = None
    baseline_time: Optional[float] = None
    proposed_time: Optional[float] = None
    improvement_percentage: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedSnapshot:
    grid_size: Tuple[int, int]
    robots: Tuple[RobotView, ...] = ()
    tasks: Tuple[TaskView, ...] = ()
    paths: Dict[Any, Tuple[Tuple[int, int], ...]] = field(default_factory=dict)
    reservations: Tuple[ReservationView, ...] = ()
    conflicts: Tuple[ConflictView, ...] = ()
    obstacles: Tuple[Tuple[int, int], ...] = ()
    shelves: Tuple[Tuple[int, int], ...] = ()
    custom_obstacles: Tuple[Tuple[int, int], ...] = ()
    dropoff_cells: Tuple[Tuple[int, int], ...] = ()
    edge_dropoff_cells: Tuple[Tuple[int, int], ...] = ()
    dropoff_station: Optional[Tuple[int, int]] = None
    selected_cell: Optional[Tuple[int, int]] = None
    metrics: MetricView = field(default_factory=MetricView)
    timestep: Optional[int] = None
    time: Optional[float] = None
    scenario_finished: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


class SnapshotNormalizer:
    """Safely normalizes arbitrary snapshot dictionaries into read-only views."""

    @staticmethod
    def _extract_pos_list(raw_list: Any) -> Tuple[Tuple[int, int], ...]:
        if not raw_list or not isinstance(raw_list, (list, tuple, set)):
            return ()
        results = []
        for item in raw_list:
            pos = SnapshotNormalizer._to_pos(item)
            if pos is not None:
                results.append(pos)
        return tuple(sorted(set(results)))

    @staticmethod
    def normalize(snapshot: Any) -> NormalizedSnapshot:
        if not isinstance(snapshot, dict):
            snapshot = {}

        # 1. Obstacles, Shelves, and Custom Obstacles
        obstacles = SnapshotNormalizer._extract_obstacles(snapshot)
        shelves = SnapshotNormalizer._extract_pos_list(snapshot.get("shelves"))
        custom_obstacles = SnapshotNormalizer._extract_pos_list(snapshot.get("custom_obstacles"))

        # Merge shelves and custom obstacles into obstacles set if provided
        for p in shelves:
            obstacles.add(p)
        for p in custom_obstacles:
            obstacles.add(p)

        # 2. Dropoff configuration
        dropoff_cells = SnapshotNormalizer._extract_pos_list(snapshot.get("dropoff_cells"))
        edge_dropoff_cells = SnapshotNormalizer._extract_pos_list(snapshot.get("edge_dropoff_cells"))
        dropoff_station = SnapshotNormalizer._to_pos(snapshot.get("dropoff_station"))
        selected_cell = SnapshotNormalizer._to_pos(snapshot.get("selected_cell"))
        scenario_finished = bool(snapshot.get("scenario_finished", False))

        # 3. Robots
        robots = SnapshotNormalizer._extract_robots(snapshot)

        # 4. Tasks
        tasks = SnapshotNormalizer._extract_tasks(snapshot)

        # 5. Paths
        paths = SnapshotNormalizer._extract_paths(snapshot, robots)

        # 6. Reservations
        reservations = SnapshotNormalizer._extract_reservations(snapshot)

        # 7. Conflicts
        conflicts = SnapshotNormalizer._extract_conflicts(snapshot)

        # 8. Metrics
        metrics = SnapshotNormalizer._extract_metrics(snapshot, tasks)

        # 9. Grid size
        grid_size = SnapshotNormalizer._determine_grid_size(
            snapshot, obstacles, robots, paths, reservations
        )

        timestep = snapshot.get("timestep")
        if timestep is None and "step" in snapshot:
            timestep = snapshot.get("step")

        time_val = snapshot.get("time")

        return NormalizedSnapshot(
            grid_size=grid_size,
            robots=tuple(robots),
            tasks=tuple(tasks),
            paths=paths,
            reservations=tuple(reservations),
            conflicts=tuple(conflicts),
            obstacles=tuple(sorted(obstacles)),
            shelves=shelves,
            custom_obstacles=custom_obstacles,
            dropoff_cells=dropoff_cells,
            edge_dropoff_cells=edge_dropoff_cells,
            dropoff_station=dropoff_station,
            selected_cell=selected_cell,
            metrics=metrics,
            timestep=timestep,
            time=float(time_val) if time_val is not None else None,
            scenario_finished=scenario_finished,
            raw=dict(snapshot) if isinstance(snapshot, dict) else {},
        )

    @staticmethod
    def _extract_obstacles(snapshot: dict) -> Set[Tuple[int, int]]:
        obstacles: Set[Tuple[int, int]] = set()

        raw_obs = snapshot.get("obstacles")
        if raw_obs is not None:
            if isinstance(raw_obs, (list, tuple, set)):
                for item in raw_obs:
                    pos = SnapshotNormalizer._to_pos(item)
                    if pos:
                        obstacles.add(pos)
            elif isinstance(raw_obs, dict):
                for key in raw_obs:
                    pos = SnapshotNormalizer._to_pos(key)
                    if pos:
                        obstacles.add(pos)

        # Also inspect warehouse if present in snapshot
        wh = snapshot.get("warehouse")
        if wh is not None:
            static_obs = getattr(wh, "static_obstacles", None)
            if isinstance(static_obs, (set, list, tuple)):
                for item in static_obs:
                    pos = SnapshotNormalizer._to_pos(item)
                    if pos:
                        obstacles.add(pos)
            dynamic_obs = getattr(wh, "dynamic_obstacles", None)
            if isinstance(dynamic_obs, (set, list, tuple)):
                for item in dynamic_obs:
                    pos = SnapshotNormalizer._to_pos(item)
                    if pos:
                        obstacles.add(pos)

        return obstacles

    @staticmethod
    def _extract_robots(snapshot: dict) -> List[RobotView]:
        robots: List[RobotView] = []
        raw_robots = snapshot.get("robots")
        if raw_robots is None:
            return robots

        if isinstance(raw_robots, dict):
            iterable = raw_robots.values()
        elif isinstance(raw_robots, (list, tuple, set)):
            iterable = raw_robots
        else:
            return robots

        for item in iterable:
            if isinstance(item, dict):
                r_id = item.get("robot_id", item.get("id"))
                pos = SnapshotNormalizer._to_pos(item.get("position", (0, 0))) or (0, 0)
                status = str(item.get("status", "UNKNOWN"))
                battery = item.get("battery")
                if battery is not None:
                    try:
                        battery = float(battery)
                    except (ValueError, TypeError):
                        battery = None
                task_id = item.get("current_task_id", item.get("active_task", item.get("task_id")))
                raw_path = item.get("path") or ()
                path_list = [
                    p for p in (SnapshotNormalizer._to_pos(pt) for pt in raw_path) if p is not None
                ]
                has_package = bool(item.get("has_package", False))
                task_stage = str(item.get("task_stage", "IDLE"))
                robots.append(
                    RobotView(
                        robot_id=r_id,
                        position=pos,
                        status=status,
                        battery=battery,
                        current_task_id=task_id,
                        path=tuple(path_list),
                        has_package=has_package,
                        task_stage=task_stage,
                    )
                )
            else:
                # Treat as robot object
                r_id = getattr(item, "robot_id", getattr(item, "id", None))
                state = getattr(item, "state", None)
                if state is not None:
                    pos = SnapshotNormalizer._to_pos(getattr(state, "position", (0, 0))) or (0, 0)
                    status = str(getattr(state, "status", "UNKNOWN"))
                    battery = getattr(state, "battery", None)
                    task_id = getattr(state, "current_task_id", None)
                    raw_path = getattr(state, "path", ())
                else:
                    pos = SnapshotNormalizer._to_pos(getattr(item, "position", (0, 0))) or (0, 0)
                    status = str(getattr(item, "status", "UNKNOWN"))
                    battery = getattr(item, "battery", None)
                    task_id = getattr(item, "current_task_id", None)
                    raw_path = getattr(item, "path", ())

                path_list = [
                    p for p in (SnapshotNormalizer._to_pos(pt) for pt in raw_path) if p is not None
                ]
                has_package = bool(getattr(item, "has_package", getattr(state, "has_package", False) if state else False))
                task_stage = str(getattr(item, "task_stage", getattr(state, "task_stage", "IDLE") if state else "IDLE"))
                robots.append(
                    RobotView(
                        robot_id=r_id,
                        position=pos,
                        status=status,
                        battery=float(battery) if battery is not None else None,
                        current_task_id=task_id,
                        path=tuple(path_list),
                        has_package=has_package,
                        task_stage=task_stage,
                    )
                )

        return robots

    @staticmethod
    def _extract_tasks(snapshot: dict) -> List[TaskView]:
        tasks: List[TaskView] = []
        raw_tasks = snapshot.get("tasks")
        if raw_tasks is None:
            # Check warehouse tasks
            wh = snapshot.get("warehouse")
            if wh is not None:
                wh_tasks = getattr(wh, "tasks", None)
                if isinstance(wh_tasks, dict):
                    raw_tasks = wh_tasks.values()
                elif isinstance(wh_tasks, (list, tuple)):
                    raw_tasks = wh_tasks

        if raw_tasks is None:
            return tasks

        if isinstance(raw_tasks, dict):
            iterable = raw_tasks.values()
        elif isinstance(raw_tasks, (list, tuple, set)):
            iterable = raw_tasks
        else:
            return tasks

        for item in iterable:
            if isinstance(item, dict):
                 t_id = item.get("task_id", item.get("id"))
                 status = item.get("status", "PENDING")
                 if hasattr(status, "value"):
                     status = status.value
                 priority = item.get("priority", 0)
                 pickup = SnapshotNormalizer._to_pos(item.get("pickup"))
                 dropoff = SnapshotNormalizer._to_pos(item.get("dropoff"))
                 assigned = item.get("assigned_robot_id")
                 is_picked_up = bool(item.get("is_picked_up", False))
                 is_finished = bool(item.get("is_finished", str(status) in ("COMPLETED", "FAILED")))
                 tasks.append(
                     TaskView(
                         task_id=t_id,
                         status=str(status),
                         priority=int(priority) if priority is not None else 0,
                         pickup=pickup,
                         dropoff=dropoff,
                         assigned_robot_id=assigned,
                         is_picked_up=is_picked_up,
                         is_finished=is_finished,
                     )
                 )
            else:
                 t_id = getattr(item, "task_id", getattr(item, "id", None))
                 raw_st = getattr(item, "status", "PENDING")
                 status = getattr(raw_st, "value", str(raw_st))
                 priority = getattr(item, "priority", 0)
                 pickup = SnapshotNormalizer._to_pos(getattr(item, "pickup", None))
                 dropoff = SnapshotNormalizer._to_pos(getattr(item, "dropoff", None))
                 assigned = getattr(item, "assigned_robot_id", None)
                 is_picked_up = bool(getattr(item, "is_picked_up", False))
                 is_finished = bool(getattr(item, "is_finished", lambda: str(status) in ("COMPLETED", "FAILED"))() if callable(getattr(item, "is_finished", None)) else getattr(item, "is_finished", False))
                 tasks.append(
                     TaskView(
                         task_id=t_id,
                         status=str(status),
                         priority=int(priority) if priority is not None else 0,
                         pickup=pickup,
                         dropoff=dropoff,
                         assigned_robot_id=assigned,
                         is_picked_up=is_picked_up,
                         is_finished=is_finished,
                     )
                 )

        return tasks

    @staticmethod
    def _extract_paths(
        snapshot: dict, robots: List[RobotView]
    ) -> Dict[Any, Tuple[Tuple[int, int], ...]]:
        paths: Dict[Any, Tuple[Tuple[int, int], ...]] = {}
        raw_paths = snapshot.get("paths")

        if isinstance(raw_paths, dict):
            for r_id, p in raw_paths.items():
                if isinstance(p, (list, tuple)):
                    clean_p = [
                        pt for pt in (SnapshotNormalizer._to_pos(x) for x in p) if pt is not None
                    ]
                    paths[r_id] = tuple(clean_p)
        elif isinstance(raw_paths, (list, tuple)):
            for item in raw_paths:
                if isinstance(item, dict) and "robot_id" in item and "path" in item:
                    clean_p = [
                        pt
                        for pt in (SnapshotNormalizer._to_pos(x) for x in item["path"])
                        if pt is not None
                    ]
                    paths[item["robot_id"]] = tuple(clean_p)

        # Fallback to robot paths if not explicitly in paths dict
        for r in robots:
            if r.robot_id not in paths and r.path:
                paths[r.robot_id] = r.path

        return paths

    @staticmethod
    def _extract_reservations(snapshot: dict) -> List[ReservationView]:
        res_list: List[ReservationView] = []
        raw_res = snapshot.get("reservations")

        if raw_res is None:
            # Check reservation table object if present
            rt = snapshot.get("reservation_table")
            if rt is not None:
                raw_res = getattr(rt, "_reservations", None)

        if raw_res is None:
            return res_list

        if isinstance(raw_res, dict):
            for key, val in raw_res.items():
                # Form 1: ((x, y), timestep): robot_id
                if isinstance(key, tuple) and len(key) == 2:
                    pos_cand, time_cand = key
                    if isinstance(pos_cand, (tuple, list)) and len(pos_cand) == 2:
                        res_list.append(
                            ReservationView(
                                robot_id=val,
                                position=(int(pos_cand[0]), int(pos_cand[1])),
                                timestep=int(time_cand) if isinstance(time_cand, (int, float)) else None,
                            )
                        )
                    # Form 2: (x, y): robot_id
                    elif isinstance(pos_cand, (int, float)) and isinstance(time_cand, (int, float)):
                        res_list.append(
                            ReservationView(
                                robot_id=val,
                                position=(int(pos_cand), int(time_cand)),
                                timestep=None,
                            )
                        )
                # Form 3: robot_id: list of reservations or positions
                elif isinstance(val, (list, tuple)):
                    for sub in val:
                        pos = SnapshotNormalizer._to_pos(getattr(sub, "position", sub))
                        timestep = getattr(sub, "timestep", None)
                        if pos:
                            res_list.append(
                                ReservationView(robot_id=key, position=pos, timestep=timestep)
                            )
        elif isinstance(raw_res, (list, tuple, set)):
            for item in raw_res:
                if isinstance(item, dict):
                    pos = SnapshotNormalizer._to_pos(item.get("position"))
                    r_id = item.get("robot_id", item.get("owner"))
                    timestep = item.get("timestep", item.get("time"))
                    if pos:
                        res_list.append(
                            ReservationView(robot_id=r_id, position=pos, timestep=timestep)
                        )
                else:
                    pos = SnapshotNormalizer._to_pos(getattr(item, "position", None))
                    r_id = getattr(item, "robot_id", getattr(item, "owner", None))
                    timestep = getattr(item, "timestep", getattr(item, "time", None))
                    if pos:
                        res_list.append(
                            ReservationView(robot_id=r_id, position=pos, timestep=timestep)
                        )

        return res_list

    @staticmethod
    def _extract_conflicts(snapshot: dict) -> List[ConflictView]:
        conflicts: List[ConflictView] = []
        raw_conflicts = snapshot.get("conflicts")
        if raw_conflicts is None:
            return conflicts

        if not isinstance(raw_conflicts, (list, tuple, set)):
            return conflicts

        for item in raw_conflicts:
            if isinstance(item, str):
                conflicts.append(
                    ConflictView(conflict_type="general", description=item, location=None, robots=())
                )
            elif isinstance(item, tuple):
                # Check if ("vertex", pos, timestep, owner) or ("edge", prev, curr, timestep, owner)
                if len(item) >= 4 and isinstance(item[0], str):
                    c_type = item[0]
                    loc = SnapshotNormalizer._to_pos(item[1])
                    owner = item[-1]
                    conflicts.append(
                        ConflictView(
                            conflict_type=c_type,
                            description=f"{c_type.title()} conflict at {loc} involving robot {owner}",
                            location=loc,
                            robots=(owner,),
                        )
                    )
                elif len(item) == 2:
                    # (robot_a, robot_b)
                    ra, rb = item
                    ra_id = getattr(ra, "robot_id", ra)
                    rb_id = getattr(rb, "robot_id", rb)
                    conflicts.append(
                        ConflictView(
                            conflict_type="path",
                            description=f"Path conflict between R{ra_id} and R{rb_id}",
                            location=None,
                            robots=(ra_id, rb_id),
                        )
                    )
            elif isinstance(item, dict):
                c_type = str(item.get("type", item.get("conflict_type", "general")))
                desc = item.get("description") or f"Conflict of type {c_type}"
                loc = SnapshotNormalizer._to_pos(item.get("location", item.get("position")))
                robs = item.get("robots") or ()
                conflicts.append(
                    ConflictView(
                        conflict_type=c_type,
                        description=desc,
                        location=loc,
                        robots=tuple(robs) if isinstance(robs, (list, tuple)) else (robs,),
                    )
                )

        return conflicts

    @staticmethod
    def _extract_metrics(snapshot: dict, tasks: List[TaskView]) -> MetricView:
        raw_metrics = snapshot.get("metrics")
        summary: Dict[str, Any] = {}

        if isinstance(raw_metrics, dict):
            summary = copy.deepcopy(raw_metrics)
        elif raw_metrics is not None and hasattr(raw_metrics, "get_summary"):
            try:
                summary = copy.deepcopy(raw_metrics.get_summary())
            except Exception:
                summary = {}

        collisions = int(summary.get("collisions", 0))
        deadlocks = int(summary.get("deadlocks", 0))
        completed = int(summary.get("tasks_completed", 0))
        total_dist = float(summary.get("total_distance", 0.0))
        wait_time = float(summary.get("waiting_time", 0.0))
        replans = int(summary.get("replanning_count", 0))
        comp_time = float(summary.get("completion_time", 0.0))

        # Completion percentage
        comp_pct = summary.get("completion_percentage")
        total_tasks = summary.get("total_tasks")
        if total_tasks is None and tasks:
            total_tasks = len(tasks)

        if comp_pct is None:
            if total_tasks and total_tasks > 0:
                comp_pct = (completed / total_tasks) * 100.0
            elif tasks:
                comp_pct = (
                    len([t for t in tasks if t.status.upper() == "COMPLETED"]) / len(tasks)
                ) * 100.0

        if comp_pct is not None:
            comp_pct = max(0.0, min(100.0, float(comp_pct)))

        # Improvement percentage
        imp_pct = summary.get("improvement")
        if imp_pct is None:
            imp_pct = summary.get("improvement_percentage")

        baseline_time = summary.get("baseline_time")
        proposed_time = summary.get("proposed_time", comp_time)

        if imp_pct is None and baseline_time is not None and proposed_time is not None:
            try:
                b_time = float(baseline_time)
                p_time = float(proposed_time)
                if b_time > 0:
                    imp_pct = ((b_time - p_time) / b_time) * 100.0
                else:
                    imp_pct = 0.0
            except (ValueError, TypeError):
                imp_pct = None

        if imp_pct is not None:
            try:
                imp_pct = float(imp_pct)
            except (ValueError, TypeError):
                imp_pct = None

        return MetricView(
            collisions=collisions,
            deadlocks=deadlocks,
            tasks_completed=completed,
            total_distance=total_dist,
            waiting_time=wait_time,
            replanning_count=replans,
            completion_time=comp_time,
            total_tasks=int(total_tasks) if total_tasks is not None else None,
            completion_percentage=comp_pct,
            baseline_time=float(baseline_time) if baseline_time is not None else None,
            proposed_time=float(proposed_time) if proposed_time is not None else None,
            improvement_percentage=imp_pct,
            raw=summary,
        )

    @staticmethod
    def _determine_grid_size(
        snapshot: dict,
        obstacles: Set[Tuple[int, int]],
        robots: List[RobotView],
        paths: Dict[Any, Tuple[Tuple[int, int], ...]],
        reservations: List[ReservationView],
    ) -> Tuple[int, int]:
        # Explicit grid_size or dimensions
        explicit = snapshot.get("grid_size", snapshot.get("dimensions"))
        if explicit and isinstance(explicit, (list, tuple)) and len(explicit) == 2:
            return int(explicit[0]), int(explicit[1])

        # Warehouse object
        wh = snapshot.get("warehouse")
        if wh and hasattr(wh, "width") and hasattr(wh, "height"):
            return int(wh.width), int(wh.height)

        # Infer from coordinates
        max_x = 0
        max_y = 0
        for x, y in obstacles:
            max_x, max_y = max(max_x, x), max(max_y, y)
        for r in robots:
            max_x, max_y = max(max_x, r.position[0]), max(max_y, r.position[1])
        for p in paths.values():
            for x, y in p:
                max_x, max_y = max(max_x, x), max(max_y, y)
        for res in reservations:
            max_x, max_y = max(max_x, res.position[0]), max(max_y, res.position[1])

        # Provide a reasonable minimum grid (e.g. 10x10) or fit bounding box
        width = max(10, max_x + 1)
        height = max(10, max_y + 1)
        return width, height

    @staticmethod
    def _to_pos(item: Any) -> Optional[Tuple[int, int]]:
        if item is None:
            return None
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            try:
                return int(item[0]), int(item[1])
            except (ValueError, TypeError):
                return None
        if isinstance(item, dict) and "x" in item and "y" in item:
            try:
                return int(item["x"]), int(item["y"])
            except (ValueError, TypeError):
                return None
        if hasattr(item, "x") and hasattr(item, "y"):
            try:
                return int(item.x), int(item.y)
            except (ValueError, TypeError):
                return None
        return None


def normalize_snapshot(snapshot: Any) -> NormalizedSnapshot:
    """Convenience function to normalize snapshot."""
    return SnapshotNormalizer.normalize(snapshot)
