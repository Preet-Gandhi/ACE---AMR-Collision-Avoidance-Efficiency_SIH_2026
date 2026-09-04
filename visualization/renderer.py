from __future__ import annotations

from typing import Any, Dict, List, Optional
from dashboard.engine import Dashboard, RenderResult


class Renderer:
    """Read-only dashboard and visualization renderer for AMR fleet snapshots."""

    def __init__(
        self,
        warehouse: Optional[Any] = None,
        robots: Optional[List[Any]] = None,
        metrics: Optional[Any] = None,
        reservation_table: Optional[Any] = None,
        color: bool = False,
    ) -> None:
        self.warehouse = warehouse
        self.robots = robots or []
        self.metrics = metrics
        self.reservation_table = reservation_table
        self.color = color
        self._dashboard = Dashboard(color=color)

    def render(
        self, snapshot: Optional[Dict[str, Any]] = None, color: Optional[bool] = None
    ) -> RenderResult:
        """Primary interface: consumes a simulation snapshot and renders the current warehouse state."""
        if snapshot is None:
            # Fallback for instance-based state if called without arguments
            snapshot = {
                "warehouse": self.warehouse,
                "robots": self.robots,
                "metrics": self.metrics,
                "reservations": self.reservation_table,
            }
        return self._dashboard.render(snapshot, color=color)

    # Legacy helper methods preserved for backward compatibility
    def render_warehouse(self, warehouse: Optional[Any] = None) -> str:
        wh = warehouse or self.warehouse
        if not wh:
            return ""
        return "\n".join(
            "".join(
                "#" if (x, y) in wh.static_obstacles | wh.dynamic_obstacles else "."
                for x in range(wh.width)
            )
            for y in range(wh.height)
        )

    def render_robots(self, robots: Optional[List[Any]] = None) -> Dict[Any, Any]:
        target = robots or self.robots
        return {r.robot_id: r.state.position for r in target}

    def render_tasks(self, tasks: List[Any]) -> Dict[Any, Any]:
        return {t.task_id: getattr(t.status, "value", str(t.status)) for t in tasks}

    def render_paths(self, robots: Optional[List[Any]] = None) -> Dict[Any, List[Any]]:
        target = robots or self.robots
        return {r.robot_id: list(r.state.path) for r in target}

    def render_reservations(self, reservation_table: Optional[Any] = None) -> Dict[Any, Any]:
        rt = reservation_table or self.reservation_table
        if rt is None:
            return {}
        res = getattr(rt, "_reservations", None)
        return res.copy() if isinstance(res, dict) else {}

    def render_metrics(self, metrics: Optional[Any] = None) -> Dict[str, Any]:
        m = metrics or self.metrics
        if m is None:
            return {}
        if hasattr(m, "get_summary"):
            return m.get_summary()
        if isinstance(m, dict):
            return m.copy()
        return {}

    def update(self) -> Dict[str, Any]:
        return {
            "warehouse": self.render_warehouse(),
            "robots": self.render_robots(),
            "metrics": self.render_metrics(),
        }
