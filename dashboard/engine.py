from __future__ import annotations

from typing import Any, Optional

try:
    from dashboard.components import ComponentFormatter
    from dashboard.grid import GridRenderer
    from dashboard.snapshot import NormalizedSnapshot, SnapshotNormalizer
except ImportError:
    from .components import ComponentFormatter
    from .grid import GridRenderer
    from .snapshot import NormalizedSnapshot, SnapshotNormalizer


class RenderResult(str):
    """Rendered dashboard string with attached metadata for programmatic access."""

    snapshot: Any
    normalized: NormalizedSnapshot

    def __new__(
        cls, content: str, snapshot: Any = None, normalized: NormalizedSnapshot = None
    ) -> RenderResult:
        obj = super().__new__(cls, content)
        obj.snapshot = snapshot
        obj.normalized = normalized
        return obj


class Dashboard:
    """Read-only dashboard engine for AMR fleet visualization."""

    def __init__(self, color: bool = False) -> None:
        self.color = color

    def render(self, snapshot: Any, color: Optional[bool] = None) -> RenderResult:
        """Consumes a snapshot and generates the formatted dashboard without mutating input state."""
        normalized = SnapshotNormalizer.normalize(snapshot)

        use_color = self.color if color is None else color
        if isinstance(snapshot, dict) and "color" in snapshot and color is None:
            use_color = bool(snapshot.get("color"))

        divider = "=" * 76
        sections = [divider]

        # Title / header banner
        time_info = []
        if normalized.timestep is not None:
            time_info.append(f"Step: {normalized.timestep}")
        if normalized.time is not None:
            time_info.append(f"Time: {normalized.time:.1f}s")
        time_str = f" [{', '.join(time_info)}]" if time_info else ""

        sections.append(f"{'ACE - AMR FLEET DASHBOARD & WAREHOUSE':^76}")
        if time_str:
            sections.append(f"{time_str:^76}")
        sections.append(divider)
        sections.append("")

        # 1. Warehouse Grid
        grid_text = GridRenderer.render(normalized, color=use_color)
        sections.append(grid_text)
        sections.append("")

        # 2. Fleet Status Table
        fleet_text = ComponentFormatter.render_fleet_status(
            normalized.robots, conflicts=normalized.conflicts, color=use_color
        )
        sections.append(fleet_text)
        sections.append("")

        # 3. Tasks Overview & Completion %
        tasks_text = ComponentFormatter.render_tasks_summary(normalized.tasks, normalized.metrics)
        sections.append(tasks_text)
        sections.append("")

        # 4. Conflicts & Safety
        conflicts_text = ComponentFormatter.render_conflicts(normalized.conflicts, color=use_color)
        sections.append(conflicts_text)
        sections.append("")

        # 5. Metrics & Performance & Improvement %
        metrics_text = ComponentFormatter.render_metrics_summary(normalized.metrics, color=use_color)
        sections.append(metrics_text)
        sections.append("")
        sections.append(divider)

        full_content = "\n".join(sections)
        return RenderResult(full_content, snapshot=snapshot, normalized=normalized)
