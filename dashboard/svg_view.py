from __future__ import annotations

import html
from typing import Dict, List, Optional, Set, Tuple
from dashboard.snapshot import NormalizedSnapshot, RobotView, TaskView


class SvgWarehouseRenderer:
    """Renders the realistic warehouse floor with shelves, common dropoff, custom obstacles, and animated AMRs."""

    @staticmethod
    def render_svg(
        snapshot: NormalizedSnapshot,
        cell_size: int = 56,
        padding: int = 36,
        shelves: Optional[Set[Tuple[int, int]]] = None,
        custom_obstacles: Optional[Set[Tuple[int, int]]] = None,
        dropoff_cells: Optional[List[Tuple[int, int]]] = None,
        selected_cell: Optional[Tuple[int, int]] = None,
    ) -> str:
        width, height = snapshot.grid_size
        svg_w = width * cell_size + padding * 2
        svg_h = height * cell_size + padding * 2

        COLOR_BG = "#0b1120"          # Dark warehouse concrete floor
        COLOR_GRID_LINE = "#1e293b"   # Subtle aisle grid line
        COLOR_SHELF_FILL = "#1e293b"  # Permanent steel shelf rack
        COLOR_SHELF_STROKE = "#475569"
        COLOR_SHELF_BEAM = "#334155"
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
        shelves_set = set(snapshot.shelves) if snapshot.shelves else (set(shelves) if shelves else set())
        custom_obs_set = (
            set(snapshot.custom_obstacles)
            if snapshot.custom_obstacles
            else (set(custom_obstacles) if custom_obstacles else set())
        )
        dropoff_list = (
            list(snapshot.dropoff_cells)
            if snapshot.dropoff_cells
            else (list(dropoff_cells) if dropoff_cells else [(5, 9), (6, 9), (7, 9), (8, 9)])
        )

        # Fallback to raw if snapshot fields were empty
        raw_snapshot = getattr(snapshot, "raw", {})
        if isinstance(raw_snapshot, dict):
            if not shelves_set and "shelves" in raw_snapshot:
                shelves_set = set(raw_snapshot["shelves"])
            if not custom_obs_set and "custom_obstacles" in raw_snapshot:
                custom_obs_set = set(raw_snapshot["custom_obstacles"])
            if not dropoff_list and "dropoff_cells" in raw_snapshot:
                dropoff_list = list(raw_snapshot["dropoff_cells"])

        if not shelves_set and not custom_obs_set:
            shelves_set = set(snapshot.obstacles)

        # Custom obstacles take precedence over racks
        shelves_set = shelves_set - custom_obs_set
        dropoff_set = set(dropoff_list)

        # Selected cell for reticle target
        target_cell = selected_cell or getattr(snapshot, "selected_cell", None)

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
            f'preserveAspectRatio="xMidYMid meet" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'style="background:{COLOR_BG}; border-radius:10px; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; user-select:none; display:block; margin:auto;">',
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
            '  <filter id="reticle-glow" x="-20%" y="-20%" width="140%" height="140%">',
            '    <feGaussianBlur stdDeviation="2" result="blur" />',
            '    <feComposite in="SourceGraphic" in2="blur" operator="over" />',
            '  </filter>',
            '</defs>',
        ]

        # 1. Coordinate Rulers (Top X labels and Left Y labels)
        for x in range(width):
            cx = padding + x * cell_size + cell_size / 2
            svg.append(
                f'<text x="{cx}" y="{padding - 12}" fill="#64748b" font-size="11" font-weight="600" text-anchor="middle">X={x}</text>'
            )

        for y in range(height):
            cy = padding + y * cell_size + cell_size / 2 + 4
            svg.append(
                f'<text x="{padding - 12}" y="{cy}" fill="#64748b" font-size="11" font-weight="600" text-anchor="end">Y={y}</text>'
            )

        # 2. Base Grid, Shelves, Dropoff Station, and Custom Obstacles
        for y in range(height):
            for x in range(width):
                rx = padding + x * cell_size
                ry = padding + y * cell_size
                pos = (x, y)

                if pos in custom_obs_set:
                    # User-placed Dynamic Custom Obstacle (ALWAYS rendered as obstacle, never rack)
                    svg.append(
                        f'<rect x="{rx+2}" y="{ry+2}" width="{cell_size-4}" height="{cell_size-4}" '
                        f'rx="4" fill="url(#hazard-stripes)" stroke="{COLOR_CUSTOM_OBS_STROKE}" stroke-width="2" />'
                    )
                    svg.append(
                        f'<text x="{rx + cell_size/2}" y="{ry + cell_size/2 + 4}" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle">⚠️</text>'
                    )
                elif pos in dropoff_set:
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
                    mid_y = ry + cell_size / 2
                    svg.append(
                        f'<line x1="{rx+4}" y1="{mid_y}" x2="{rx+cell_size-4}" y2="{mid_y}" stroke="{COLOR_SHELF_BEAM}" stroke-width="2" />'
                    )
                    svg.append(
                        f'<text x="{rx + cell_size/2}" y="{ry + cell_size/2 - 4}" fill="#475569" font-size="9" font-weight="bold" text-anchor="middle">RACK</text>'
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

        # 3. Target Reticle for Selected Cell (Interactive feedback)
        if target_cell is not None and 0 <= target_cell[0] < width and 0 <= target_cell[1] < height:
            sx = padding + target_cell[0] * cell_size
            sy = padding + target_cell[1] * cell_size
            c_len = 10
            # Reticle background tint & pulsing border
            svg.append(
                f'<rect x="{sx}" y="{sy}" width="{cell_size}" height="{cell_size}" '
                f'fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 2" rx="3" filter="url(#reticle-glow)" />'
            )
            # Corner targeting brackets
            svg.append(f'<path d="M {sx+2} {sy+2+c_len} L {sx+2} {sy+2} L {sx+2+c_len} {sy+2}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')
            svg.append(f'<path d="M {sx+cell_size-2-c_len} {sy+2} L {sx+cell_size-2} {sy+2} L {sx+cell_size-2} {sy+2+c_len}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')
            svg.append(f'<path d="M {sx+2} {sy+cell_size-2-c_len} L {sx+2} {sy+cell_size-2} L {sx+2+c_len} {sy+cell_size-2}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')
            svg.append(f'<path d="M {sx+cell_size-2-c_len} {sy+cell_size-2} L {sx+cell_size-2} {sy+cell_size-2} L {sx+cell_size-2} {sy+cell_size-2-c_len}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')

        # 4. Pickups (P1, P2...) in aisles
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

        # 5. Real Planned Paths (Trail underneath robots)
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

        # 6. AMRs — render the authoritative simulator position only.
        # Do NOT animate an independent SVG clock: Streamlit snapshots are
        # discrete simulation frames, so the visual must always match state.
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

            cx = padding + r.position[0] * cell_size + cell_size / 2
            cy = padding + r.position[1] * cell_size + cell_size / 2
            r_radius = 16

            if is_conflicted:
                svg.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r_radius + 5}" fill="none" stroke="#ef4444" stroke-width="3" filter="url(#conflict-glow)" />'
                )
            svg.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r_radius}" fill="{state_color}" stroke="#ffffff" stroke-width="2" />'
            )
            svg.append(
                f'<text x="{cx}" y="{cy + 4.5}" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">{html.escape(r_id)}</text>'
            )

            # Package indicator comes from the normalized simulator snapshot.
            if getattr(r, "has_package", False):
                svg.append(
                    f'<rect x="{cx + 6}" y="{cy - 18}" width="14" height="14" rx="2" fill="#f59e0b" stroke="#b45309" stroke-width="1.5" />'
                )
                svg.append(
                    f'<text x="{cx + 13}" y="{cy - 7}" fill="#78350f" font-size="9" font-weight="bold" text-anchor="middle">📦</text>'
                )

        svg.append('</svg>')
        return "\n".join(svg)
