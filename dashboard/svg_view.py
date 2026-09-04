from __future__ import annotations

import html
from typing import Dict, List, Set, Tuple
from dashboard.snapshot import NormalizedSnapshot, RobotView, TaskView


class SvgWarehouseRenderer:
    """Renders the simplified warehouse floor with animated moving AMR robots."""

    @staticmethod
    def render_svg(
        snapshot: NormalizedSnapshot,
        cell_size: int = 58,
        padding: int = 32,
    ) -> str:
        width, height = snapshot.grid_size
        svg_w = width * cell_size + padding * 2
        svg_h = height * cell_size + padding * 2

        # Color palette
        COLOR_BG = "#0f172a"          # Dark slate floor
        COLOR_GRID_LINE = "#1e293b"   # Subtle grid line
        COLOR_SHELF_FILL = "#1e293b"  # Warehouse shelf rack
        COLOR_SHELF_STROKE = "#475569"
        COLOR_SHELF_ACCENT = "#334155"

        ROBOT_COLORS = {
            "MOVING": "#10b981",    # 🟢 Green
            "WAITING": "#f59e0b",   # 🟡 Yellow
            "CONFLICT": "#ef4444",  # 🔴 Red
            "IDLE": "#94a3b8",      # ⚪ Gray
        }

        # Identify conflicts
        conflict_cells: Set[Tuple[int, int]] = set()
        conflicted_robots: Set[str] = set()
        for c in snapshot.conflicts:
            if c.location:
                conflict_cells.add(c.location)
            for r in c.robots:
                conflicted_robots.add(str(r))

        obstacles: Set[Tuple[int, int]] = set(snapshot.obstacles)

        # Map task pickups and dropoffs
        pickups: Dict[Tuple[int, int], str] = {}
        dropoffs: Dict[Tuple[int, int], str] = {}
        for idx, t in enumerate(snapshot.tasks, 1):
            lbl = f"P{idx}"
            if t.pickup:
                pickups[t.pickup] = lbl
            d_lbl = f"D{idx}"
            if t.dropoff:
                dropoffs[t.dropoff] = d_lbl

        svg = [
            f'<svg viewBox="0 0 {svg_w} {svg_h}" width="100%" height="auto" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'style="background:{COLOR_BG}; border-radius:10px; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; user-select:none;">',
            '<defs>',
            '  <marker id="path-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
            '    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8" />',
            '  </marker>',
            '  <filter id="conflict-glow" x="-20%" y="-20%" width="140%" height="140%">',
            '    <feGaussianBlur stdDeviation="3" result="blur" />',
            '    <feComposite in="SourceGraphic" in2="blur" operator="over" />',
            '  </filter>',
            '</defs>',
        ]

        # 1. Floor grid cells
        for y in range(height):
            for x in range(width):
                rx = padding + x * cell_size
                ry = padding + y * cell_size
                pos = (x, y)

                if pos in obstacles:
                    # Warehouse Shelf / Obstacle Block
                    svg.append(
                        f'<rect x="{rx+2}" y="{ry+2}" width="{cell_size-4}" height="{cell_size-4}" '
                        f'rx="4" fill="{COLOR_SHELF_FILL}" stroke="{COLOR_SHELF_STROKE}" stroke-width="1.5" />'
                    )
                    # Shelf beam lines
                    mid_y = ry + cell_size / 2
                    svg.append(
                        f'<line x1="{rx+5}" y1="{mid_y}" x2="{rx+cell_size-5}" y2="{mid_y}" stroke="{COLOR_SHELF_ACCENT}" stroke-width="1.5" />'
                    )
                elif pos in conflict_cells:
                    # Conflict Cell highlight
                    svg.append(
                        f'<rect x="{rx+1}" y="{ry+1}" width="{cell_size-2}" height="{cell_size-2}" '
                        f'rx="4" fill="rgba(239, 68, 68, 0.25)" stroke="#ef4444" stroke-width="2" filter="url(#conflict-glow)" />'
                    )
                else:
                    # Clean empty floor cell
                    svg.append(
                        f'<rect x="{rx}" y="{ry}" width="{cell_size}" height="{cell_size}" '
                        f'fill="#0f172a" stroke="{COLOR_GRID_LINE}" stroke-width="1" />'
                    )

        # 2. Pickups (P) & Dropoffs (D)
        for (px, py), p_lbl in pickups.items():
            if (px, py) not in obstacles:
                cx = padding + px * cell_size + cell_size / 2
                cy = padding + py * cell_size + cell_size / 2
                svg.append(
                    f'<rect x="{cx - 16}" y="{cy - 12}" width="32" height="24" rx="4" '
                    f'fill="#1e3a8a" stroke="#3b82f6" stroke-width="1.5" />'
                )
                svg.append(
                    f'<text x="{cx}" y="{cy + 4}" fill="#bfdbfe" font-size="11" font-weight="bold" text-anchor="middle">{p_lbl}</text>'
                )

        for (dx, dy), d_lbl in dropoffs.items():
            if (dx, dy) not in obstacles:
                cx = padding + dx * cell_size + cell_size / 2
                cy = padding + dy * cell_size + cell_size / 2
                svg.append(
                    f'<rect x="{cx - 16}" y="{cy - 12}" width="32" height="24" rx="4" '
                    f'fill="#064e3b" stroke="#10b981" stroke-width="1.5" />'
                )
                svg.append(
                    f'<text x="{cx}" y="{cy + 4}" fill="#a7f3d0" font-size="11" font-weight="bold" text-anchor="middle">{d_lbl}</text>'
                )

        # 3. Planned Paths (Subtle trail underneath robots)
        for idx, r in enumerate(snapshot.robots, 1):
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
                        f'<polyline points="{polyline_str}" fill="none" stroke="#38bdf8" stroke-width="2" '
                        f'stroke-dasharray="5 3" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#path-arrow)" opacity="0.65" />'
                    )

        # 4. Animated Robots (Smooth movement along assigned paths)
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

            r_radius = 17

            # Check if robot has a path to animate along
            full_pts = [r.position] + [p for p in r.path if p != r.position]
            if len(full_pts) >= 2 and st != "WAITING":
                # Build SVG path trajectory
                d_cmds = [f"M {padding + full_pts[0][0]*cell_size + cell_size/2} {padding + full_pts[0][1]*cell_size + cell_size/2}"]
                for pt in full_pts[1:]:
                    d_cmds.append(f"L {padding + pt[0]*cell_size + cell_size/2} {padding + pt[1]*cell_size + cell_size/2}")
                path_d = " ".join(d_cmds)

                # Duration proportional to path length (e.g. 1.2s per waypoint step)
                duration = max(3.0, len(full_pts) * 1.3)

                svg.append('<g>')
                svg.append(
                    f'  <animateMotion dur="{duration:.1f}s" repeatCount="indefinite" path="{path_d}" '
                    f'calcMode="linear" keyTimes="0; 0.8; 1" keyPoints="0; 1; 1" />'
                )
                # Outer glow if conflicted
                if is_conflicted:
                    svg.append(
                        f'  <circle cx="0" cy="0" r="{r_radius + 4}" fill="none" stroke="#ef4444" stroke-width="2" filter="url(#conflict-glow)" />'
                    )
                # Robot circular body
                svg.append(
                    f'  <circle cx="0" cy="0" r="{r_radius}" fill="{state_color}" stroke="#ffffff" stroke-width="2" />'
                )
                # Robot text
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
