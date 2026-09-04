from __future__ import annotations

import html
from typing import Dict, List, Set, Tuple
from dashboard.snapshot import NormalizedSnapshot, RobotView, TaskView


class SvgWarehouseRenderer:
    """Renders the realistic warehouse floor with shelves, common dropoff, custom obstacles, and animated AMRs."""

    @staticmethod
    def render_svg(
        snapshot: NormalizedSnapshot,
        cell_size: int = 56,
        padding: int = 32,
        shelves: Optional[Set[Tuple[int, int]]] = None,
        custom_obstacles: Optional[Set[Tuple[int, int]]] = None,
        dropoff_cells: Optional[List[Tuple[int, int]]] = None,
    ) -> str:
        width, height = snapshot.grid_size
        svg_w = width * cell_size + padding * 2
        svg_h = height * cell_size + padding * 2

        COLOR_BG = "#0b1120"          # Dark warehouse concrete floor
        COLOR_GRID_LINE = "#1e293b"   # Subtle aisle grid line
        COLOR_SHELF_FILL = "#1e293b"  # Permanent steel shelf rack
        COLOR_SHELF_STROKE = "#475569"
        COLOR_SHELF_BEAM = "#334155"
        COLOR_CUSTOM_OBS_FILL = "#7c2d12"    # Rust / amber hazard block
        COLOR_CUSTOM_OBS_STROKE = "#ea580c"  # Orange hazard border
        COLOR_DROPOFF_BG = "#064e3b"         # Green dropoff bay
        COLOR_DROPOFF_BORDER = "#10b981"

        ROBOT_COLORS = {
            "MOVING": "#10b981",    # 🟢 Green
            "WAITING": "#f59e0b",   # 🟡 Yellow
            "CONFLICT": "#ef4444",  # 🔴 Red
            "IDLE": "#94a3b8",      # ⚪ Gray
        }

        # Segregate shelves and custom obstacles
        raw_snapshot = getattr(snapshot, "raw", {})
        if isinstance(raw_snapshot, dict):
            shelves_set = set(raw_snapshot.get("shelves", []))
            custom_obs_set = set(raw_snapshot.get("custom_obstacles", []))
            dropoff_list = raw_snapshot.get("dropoff_cells", [(5, 9), (6, 9), (7, 9), (8, 9)])
        else:
            shelves_set = shelves or set()
            custom_obs_set = custom_obstacles or set()
            dropoff_list = dropoff_cells or [(5, 9), (6, 9), (7, 9), (8, 9)]

        # Fallback if raw was empty
        if not shelves_set and not custom_obs_set:
            shelves_set = set(snapshot.obstacles)

        dropoff_set = set(dropoff_list)

        # Identify conflicts
        conflict_cells: Set[Tuple[int, int]] = set()
        conflicted_robots: Set[str] = set()
        for c in snapshot.conflicts:
            if c.location:
                conflict_cells.add(c.location)
            for r in c.robots:
                conflicted_robots.add(str(r))

        # Pickups (from tasks)
        pickups: Dict[Tuple[int, int], str] = {}
        for idx, t in enumerate(snapshot.tasks, 1):
            if t.pickup and t.pickup not in shelves_set and t.pickup not in custom_obs_set:
                pickups[t.pickup] = f"P{idx}"

        svg = [
            f'<svg viewBox="0 0 {svg_w} {svg_h}" width="100%" height="auto" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'style="background:{COLOR_BG}; border-radius:10px; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; user-select:none;">',
            '<defs>',
            '  <marker id="path-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            '    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8" />',
            '  </marker>',
            '  <pattern id="hazard-stripes" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">',
            '    <line x1="0" y1="0" x2="0" y2="10" stroke="#f97316" stroke-width="3" />',
            '    <line x1="5" y1="0" x2="5" y2="10" stroke="#7c2d12" stroke-width="3" />',
            '  </pattern>',
            '  <filter id="conflict-glow" x="-20%" y="-20%" width="140%" height="140%">',
            '    <feGaussianBlur stdDeviation="3" result="blur" />',
            '    <feComposite in="SourceGraphic" in2="blur" operator="over" />',
            '  </filter>',
            '</defs>',
        ]

        # 1. Base Grid, Shelves, Dropoff Station, and Custom Obstacles
        for y in range(height):
            for x in range(width):
                rx = padding + x * cell_size
                ry = padding + y * cell_size
                pos = (x, y)

                if pos in dropoff_set:
                    # Common Dropoff Bay Cell
                    svg.append(
                        f'<rect x="{rx}" y="{ry}" width="{cell_size}" height="{cell_size}" '
                        f'fill="{COLOR_DROPOFF_BG}" stroke="{COLOR_DROPOFF_BORDER}" stroke-width="1.5" opacity="0.85" />'
                    )
                elif pos in shelves_set:
                    # Permanent Storage Shelf Rack (████)
                    svg.append(
                        f'<rect x="{rx+2}" y="{ry+2}" width="{cell_size-4}" height="{cell_size-4}" '
                        f'rx="3" fill="{COLOR_SHELF_FILL}" stroke="{COLOR_SHELF_STROKE}" stroke-width="1.5" />'
                    )
                    # Shelf beam dividers
                    mid_y = ry + cell_size / 2
                    svg.append(
                        f'<line x1="{rx+4}" y1="{mid_y}" x2="{rx+cell_size-4}" y2="{mid_y}" stroke="{COLOR_SHELF_BEAM}" stroke-width="2" />'
                    )
                    svg.append(
                        f'<text x="{rx + cell_size/2}" y="{ry + cell_size/2 - 4}" fill="#475569" font-size="9" font-weight="bold" text-anchor="middle">RACK</text>'
                    )
                elif pos in custom_obs_set:
                    # User-placed Dynamic Custom Obstacle (██)
                    svg.append(
                        f'<rect x="{rx+2}" y="{ry+2}" width="{cell_size-4}" height="{cell_size-4}" '
                        f'rx="4" fill="url(#hazard-stripes)" stroke="{COLOR_CUSTOM_OBS_STROKE}" stroke-width="2" />'
                    )
                    svg.append(
                        f'<text x="{rx + cell_size/2}" y="{ry + cell_size/2 + 4}" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle">⚠️</text>'
                    )
                elif pos in conflict_cells:
                    # Conflict Cell highlight
                    svg.append(
                        f'<rect x="{rx+1}" y="{ry+1}" width="{cell_size-2}" height="{cell_size-2}" '
                        f'rx="4" fill="rgba(239, 68, 68, 0.3)" stroke="#ef4444" stroke-width="2" filter="url(#conflict-glow)" />'
                    )
                else:
                    # Clean Aisle Floor
                    svg.append(
                        f'<rect x="{rx}" y="{ry}" width="{cell_size}" height="{cell_size}" '
                        f'fill="#0b1120" stroke="{COLOR_GRID_LINE}" stroke-width="1" />'
                    )

        # Dropoff Station Banner across the dropoff cells
        if dropoff_list:
            min_dx = min(p[0] for p in dropoff_list)
            max_dx = max(p[0] for p in dropoff_list)
            dy = dropoff_list[0][1]
            station_x = padding + min_dx * cell_size
            station_y = padding + dy * cell_size
            station_w = (max_dx - min_dx + 1) * cell_size
            svg.append(
                f'<text x="{station_x + station_w/2}" y="{station_y + cell_size/2 + 5}" fill="#a7f3d0" '
                f'font-size="13" font-weight="700" letter-spacing="1.5px" text-anchor="middle">⬇ DROPOFF STATION ⬇</text>'
            )

        # 2. Pickups (P1, P2...) in aisles
        for (px, py), p_lbl in pickups.items():
            cx = padding + px * cell_size + cell_size / 2
            cy = padding + py * cell_size + cell_size / 2
            svg.append(
                f'<rect x="{cx - 16}" y="{cy - 12}" width="32" height="24" rx="4" '
                f'fill="#1e3a8a" stroke="#3b82f6" stroke-width="1.5" />'
            )
            svg.append(
                f'<text x="{cx}" y="{cy + 5}" fill="#bfdbfe" font-size="11" font-weight="bold" text-anchor="middle">{p_lbl}</text>'
            )

        # 3. Real Planned Paths (Subtle trail underneath robots)
        for r in snapshot.robots:
            r_path = r.path
            if len(r_path) >= 1:
                full_pts = [r.position] + [p for p in r_path if p != r.position]
                if len(full_pts) >= 2:
                    pts = []
                    for px, py in full_pts:
                        cx = padding + px * cell_size + cell_size / 2
                        cy = padding + py * cell_size + cell_size / 2
                        pts.append(f"{cx},{cy}")

                    polyline_str = " ".join(pts)
                    svg.append(
                        f'<polyline points="{polyline_str}" fill="none" stroke="#38bdf8" stroke-width="2.5" '
                        f'stroke-dasharray="6 3" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#path-arrow)" opacity="0.75" />'
                    )

        # 4. Animated AMRs (Moving smoothly along their real paths)
        for r in snapshot.robots:
            r_id = f"R{r.robot_id}" if r.robot_id is not None else "R?"
            st = r.status.upper() if r.status else "UNKNOWN"
            is_conflicted = str(r.robot_id) in conflicted_robots or r.position in conflict_cells

            if is_conflicted:
                state_color = ROBOT_COLORS["CONFLICT"]
            elif st == "WAITING":
                state_color = ROBOT_COLORS["WAITING"]
            elif st == "MOVING":
                state_color = ROBOT_COLORS["MOVING"]
            else:
                state_color = ROBOT_COLORS["IDLE"]

            r_radius = 16

            # Real planned path traversal
            full_pts = [r.position] + [p for p in r.path if p != r.position]
            if len(full_pts) >= 2 and st != "WAITING":
                d_cmds = [f"M {padding + full_pts[0][0]*cell_size + cell_size/2} {padding + full_pts[0][1]*cell_size + cell_size/2}"]
                for pt in full_pts[1:]:
                    d_cmds.append(f"L {padding + pt[0]*cell_size + cell_size/2} {padding + pt[1]*cell_size + cell_size/2}")
                path_d = " ".join(d_cmds)

                # Duration based on actual path length (approx 1.2s per waypoint)
                duration = max(3.0, len(full_pts) * 1.2)

                svg.append('<g>')
                svg.append(
                    f'  <animateMotion dur="{duration:.1f}s" repeatCount="indefinite" path="{path_d}" '
                    f'calcMode="linear" keyTimes="0; 0.8; 1" keyPoints="0; 1; 1" />'
                )
                if is_conflicted:
                    svg.append(
                        f'  <circle cx="0" cy="0" r="{r_radius + 4}" fill="none" stroke="#ef4444" stroke-width="2" filter="url(#conflict-glow)" />'
                    )
                svg.append(
                    f'  <circle cx="0" cy="0" r="{r_radius}" fill="{state_color}" stroke="#ffffff" stroke-width="2" />'
                )
                svg.append(
                    f'  <text x="0" y="4.5" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">{html.escape(r_id)}</text>'
                )
                svg.append('</g>')
            else:
                # Stationary robot (WAITING, IDLE, or end of path)
                cx = padding + r.position[0] * cell_size + cell_size / 2
                cy = padding + r.position[1] * cell_size + cell_size / 2

                if is_conflicted:
                    svg.append(
                        f'<circle cx="{cx}" cy="{cy}" r="{r_radius + 4}" fill="none" stroke="#ef4444" stroke-width="2" filter="url(#conflict-glow)" />'
                    )
                svg.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r_radius}" fill="{state_color}" stroke="#ffffff" stroke-width="2" />'
                )
                svg.append(
                    f'<text x="{cx}" y="{cy + 4.5}" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">{html.escape(r_id)}</text>'
                )

        svg.append('</svg>')
        return "\n".join(svg)
