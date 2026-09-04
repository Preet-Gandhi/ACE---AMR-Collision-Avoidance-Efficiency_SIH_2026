from __future__ import annotations

from typing import Optional, Set, Tuple
from dashboard.snapshot import ConflictView, MetricView, NormalizedSnapshot, RobotView, TaskView


class ComponentFormatter:
    """Formats individual dashboard sections and cards with optional ANSI coloring."""

    @staticmethod
    def render_fleet_status(
        robots: Tuple[RobotView, ...],
        conflicts: Tuple[ConflictView, ...] = (),
        color: bool = False,
    ) -> str:
        lines = ["--- Fleet Status ---"]
        if not robots:
            lines.append("No active robots reported.")
            return "\n".join(lines)

        C_RESET = "\033[0m" if color else ""
        C_GREEN = "\033[92m" if color else ""
        C_YELLOW = "\033[93m" if color else ""
        C_RED = "\033[91m" if color else ""

        conflicted_robots: Set[str] = set()
        for c in conflicts:
            for r in c.robots:
                conflicted_robots.add(str(r))

        for r in robots:
            r_id = f"R{r.robot_id}" if r.robot_id is not None else "R?"
            pos_str = f"({r.position[0]}, {r.position[1]})"
            raw_status = (r.availability_state if r.availability_state not in {"", "UNKNOWN"}
                          else r.status).upper()
            is_conflicted = str(r.robot_id) in conflicted_robots

            if is_conflicted:
                status_str = f"{raw_status} (CONFLICT)"
                color_code = C_RED
            elif raw_status == "WAITING":
                status_str = "WAITING"
                color_code = C_YELLOW
            elif raw_status == "MOVING":
                status_str = "MOVING"
                color_code = C_GREEN
            elif raw_status == "DISCHARGED":
                status_str = "DISCHARGED"
                color_code = C_RED
            else:
                status_str = raw_status
                color_code = ""

            battery_val = f"{r.battery:.1f}%" if r.battery is not None else "N/A"
            battery_str = f"Battery {battery_val}"

            if r.current_task_id is not None:
                task_str = f"Task #{r.current_task_id}"
            else:
                task_str = "None"

            # Clean format: R1 | MOVING | Battery 95% | Task #3
            core_info = f"{r_id} | {status_str:<18} | {battery_str:<13} | {task_str:<10} | Pos {pos_str}"
            if color_code:
                core_info = f"{color_code}{core_info}{C_RESET}"
            lines.append(core_info)

            # Planned path line if available
            if r.path:
                path_preview = " -> ".join(f"({x},{y})" for x, y in r.path[:6])
                if len(r.path) > 6:
                    path_preview += f" ... (+{len(r.path) - 6} more)"
                lines.append(f"  |-> Planned Path: {path_preview}")

        return "\n".join(lines)

    @staticmethod
    def render_tasks_summary(tasks: Tuple[TaskView, ...], metrics: MetricView) -> str:
        lines = ["--- Tasks Overview ---"]
        if not tasks:
            if metrics.total_tasks is not None or metrics.tasks_completed > 0:
                lines.append(f"Tasks Completed: {metrics.tasks_completed} / {metrics.total_tasks or '?'}")
            else:
                lines.append("No task records available.")

        completed_count = 0
        in_progress_count = 0
        assigned_count = 0
        pending_count = 0
        failed_count = 0

        for t in tasks:
            st = t.status.upper()
            if st == "COMPLETED":
                completed_count += 1
            elif st == "IN_PROGRESS":
                in_progress_count += 1
            elif st == "ASSIGNED":
                assigned_count += 1
            elif st == "PENDING":
                pending_count += 1
            elif st == "FAILED":
                failed_count += 1

        if tasks:
            lines.append(
                f"Total Tasks: {len(tasks)} | Completed: {completed_count} | In Progress: {in_progress_count} | Assigned: {assigned_count} | Pending: {pending_count} | Failed: {failed_count}"
            )

        # Completion percentage
        comp_pct = metrics.completion_percentage
        if comp_pct is not None:
            bar_len = 20
            filled = int(round((comp_pct / 100.0) * bar_len))
            bar = "=" * filled + "-" * (bar_len - filled)
            lines.append(f"Completion Percentage: {comp_pct:.1f}% [{bar}]")
        else:
            lines.append("Completion Percentage: N/A")

        return "\n".join(lines)

    @staticmethod
    def render_conflicts(conflicts: Tuple[ConflictView, ...], color: bool = False) -> str:
        lines = ["--- Safety & Conflict Monitoring ---"]
        if not conflicts:
            lines.append("Active Conflicts: 0 (No safety conflicts detected)")
            return "\n".join(lines)

        C_RESET = "\033[0m" if color else ""
        C_RED = "\033[1;91m" if color else ""

        lines.append(f"{C_RED}Active Conflicts Detected: {len(conflicts)}{C_RESET}")
        for i, c in enumerate(conflicts, 1):
            loc_str = f" at {c.location}" if c.location else ""
            robs_str = f" involving {c.robots}" if c.robots else ""
            lines.append(f"  {C_RED}[!]{C_RESET} [{c.conflict_type.upper()}]{loc_str}{robs_str}: {c.description}")
        return "\n".join(lines)

    @staticmethod
    def render_metrics_summary(metrics: MetricView, color: bool = False) -> str:
        lines = ["--- Metrics & Fleet Performance ---"]
        C_RESET = "\033[0m" if color else ""
        C_GREEN = "\033[92m" if color else ""

        # Primary KPIs in compact card format
        lines.append(
            f"Collisions: {metrics.collisions} | Deadlocks: {metrics.deadlocks} | Replanning Count: {metrics.replanning_count}"
        )
        lines.append(
            f"Tasks Completed: {metrics.tasks_completed} | Total Travel Distance: {metrics.total_distance:.1f}m | Total Waiting Time: {metrics.waiting_time:.2f}s"
        )

        time_line = f"Completion Time: {metrics.completion_time:.2f}s"
        if metrics.baseline_time is not None:
            time_line += f" | Baseline Time: {metrics.baseline_time:.2f}s"
        lines.append(time_line)

        # Improvement percentage
        if metrics.improvement_percentage is not None:
            sign = "+" if metrics.improvement_percentage > 0 else ""
            imp_text = f"Improvement Percentage: {sign}{metrics.improvement_percentage:.2f}%"
            if color and metrics.improvement_percentage > 0:
                imp_text = f"{C_GREEN}{imp_text}{C_RESET}"
            lines.append(imp_text)
        else:
            lines.append("Improvement Percentage: N/A")

        return "\n".join(lines)
