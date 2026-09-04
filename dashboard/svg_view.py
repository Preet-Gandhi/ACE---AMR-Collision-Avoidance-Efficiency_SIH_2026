from __future__ import annotations

import html
from typing import Dict, List, Optional, Set, Tuple
from dashboard.snapshot import NormalizedSnapshot, RobotView, TaskView


class SvgWarehouseRenderer:
    """Renders the realistic warehouse floor with shelves, charging stations, common dropoff, custom obstacles, and AMRs."""

    @staticmethod
    def render_svg(
        snapshot: NormalizedSnapshot,
        cell_size: int = 42,
        padding: int = 24,
        shelves: Optional[Set[Tuple[int, int]]] = None,
        custom_obstacles: Optional[Set[Tuple[int, int]]] = None,
        dropoff_cells: Optional[List[Tuple[int, int]]] = None,
        selected_cell: Optional[Tuple[int, int]] = None,
    ) -> str:
        width, height = snapshot.grid_size
        if cell_size == 42 and (width > 20 or height > 16):
            cell_size = max(22, min(42, 640 // max(width, height)))

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
            "MOVING": "#10b981",       # 🟢 Green
            "WAITING": "#f59e0b",      # 🟡 Yellow
            "CONFLICT": "#ef4444",     # 🔴 Red
            "IDLE": "#94a3b8",         # ⚪ Gray
            "DISCHARGED": "#dc2626",
            "OFFLINE": "#7f1d1d",
            "CHARGING": "#3b82f6",     # ⚡ Blue
            "GOING_TO_CHARGER": "#f59e0b",
            "LOW_BATTERY": "#ef4444",  # 🪫 Red
        }

        # Segregate shelves and custom obstacles
        shelves_set = set(snapshot.shelves) if snapshot.shelves else (set(shelves) if shelves else set())
        custom_obs_set = (
            set(snapshot.custom_obstacles)
            if snapshot.custom_obstacles
            else (set(custom_obstacles) if custom_obstacles else set())
        )
        edge_dropoff_set = (
            set(snapshot.edge_dropoff_cells)
            if snapshot.edge_dropoff_cells
            else (set(dropoff_cells) if dropoff_cells else set(snapshot.dropoff_cells))
        )

        # Fallback to raw if snapshot fields were empty
        raw_snapshot = getattr(snapshot, "raw", {})
        if isinstance(raw_snapshot, dict):
            if not shelves_set and "shelves" in raw_snapshot:
                shelves_set = set(raw_snapshot["shelves"])
            if not custom_obs_set and "custom_obstacles" in raw_snapshot:
                custom_obs_set = set(raw_snapshot["custom_obstacles"])
            if not edge_dropoff_set and "edge_dropoff_cells" in raw_snapshot:
                edge_dropoff_set = set(raw_snapshot["edge_dropoff_cells"])

        if not shelves_set and not custom_obs_set:
            shelves_set = set(snapshot.obstacles)

        # Custom obstacles take precedence over racks
        shelves_set = shelves_set - custom_obs_set

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

        # Charging stations mapping
        chargers_map: Dict[Tuple[int, int], Any] = {}
        for ch in snapshot.charging_stations:
            chargers_map[ch.position] = ch

        ROBOT_PATH_COLORS = ["#38bdf8", "#c084fc", "#34d399", "#fbbf24", "#f472b6"]

        svg = [
            f'<svg id="warehouse-grid-svg" tabindex="0" viewBox="0 0 {svg_w} {svg_h}" width="100%" height="auto" '
            f'preserveAspectRatio="xMidYMid meet" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'style="background:{COLOR_BG}; border-radius:8px; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; user-select:none; display:block; margin:auto; max-height:48vh; outline:none;">',
            '<defs>',
        ]
        for i, c in enumerate(ROBOT_PATH_COLORS):
            svg.append(
                f'  <marker id="path-arrow-{i}" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                f'    <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{c}" />'
                f'  </marker>'
            )
        svg.extend([
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
        ])

        # 1. Coordinate Rulers (Top X labels and Left Y labels)
        font_sz = 11 if cell_size >= 32 else 9
        for x in range(width):
            cx = padding + x * cell_size + cell_size / 2
            svg.append(
                f'<text x="{cx}" y="{padding - 10}" fill="#64748b" font-size="{font_sz}" font-weight="600" text-anchor="middle">X={x}</text>'
            )

        for y in range(height):
            cy = padding + y * cell_size + cell_size / 2 + 4
            svg.append(
                f'<text x="{padding - 10}" y="{cy}" fill="#64748b" font-size="{font_sz}" font-weight="600" text-anchor="end">Y={y}</text>'
            )

        # Collect ONLY currently active dropoff targets for existing tasks
        active_dropoffs: Dict[Tuple[int, int], List[str]] = {}
        for idx, t in enumerate(snapshot.tasks, 1):
            if t.dropoff and not t.is_finished and t.dropoff not in shelves_set and t.dropoff not in custom_obs_set:
                active_dropoffs.setdefault(t.dropoff, []).append(f"D{idx}")

        # 2. Base Grid, Shelves, Charging Pads, Active Dropoffs, and Custom Obstacles
        for y in range(height):
            for x in range(width):
                rx = padding + x * cell_size
                ry = padding + y * cell_size
                pos = (x, y)

                if pos in custom_obs_set:
                    # User-placed Dynamic Custom Obstacle
                    svg.append(
                        f'<rect x="{rx+2}" y="{ry+2}" width="{cell_size-4}" height="{cell_size-4}" '
                        f'rx="4" fill="url(#hazard-stripes)" stroke="{COLOR_CUSTOM_OBS_STROKE}" stroke-width="2" />'
                    )
                    svg.append(
                        f'<text x="{rx + cell_size/2}" y="{ry + cell_size/2 + 4}" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle">⚠️</text>'
                    )
                elif pos in chargers_map:
                    ch_info = chargers_map[pos]
                    ch_status = ch_info.status.upper()
                    if ch_status == "OCCUPIED":
                        ch_stroke = "#10b981"
                        ch_bg = "rgba(16, 185, 129, 0.25)"
                        ch_txt = "#6ee7b7"
                    elif ch_status == "RESERVED":
                        ch_stroke = "#f59e0b"
                        ch_bg = "rgba(245, 158, 11, 0.25)"
                        ch_txt = "#fde68a"
                    else:
                        ch_stroke = "#38bdf8"
                        ch_bg = "rgba(56, 189, 248, 0.15)"
                        ch_txt = "#93c5fd"

                    svg.append(
                        f'<rect x="{rx+1}" y="{ry+1}" width="{cell_size-2}" height="{cell_size-2}" '
                        f'rx="3" fill="{ch_bg}" stroke="{ch_stroke}" stroke-width="1.5" />'
                    )
                    svg.append(
                        f'<text x="{rx + cell_size/2}" y="{ry + cell_size/2 + 4}" fill="{ch_txt}" font-size="{font_sz}" font-weight="bold" text-anchor="middle">⚡</text>'
                    )
                elif pos in active_dropoffs:
                    # ONLY currently active dropoff cells receive the teal/green highlight
                    svg.append(
                        f'<rect x="{rx+1}" y="{ry+1}" width="{cell_size-2}" height="{cell_size-2}" '
                        f'rx="3" fill="{COLOR_DROPOFF_BG}" stroke="{COLOR_DROPOFF_BORDER}" stroke-width="1.5" opacity="0.85" />'
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
                    if cell_size >= 28:
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

        # 3. Target Reticle for Selected Cell (Interactive feedback)
        if target_cell is not None and 0 <= target_cell[0] < width and 0 <= target_cell[1] < height:
            sx = padding + target_cell[0] * cell_size
            sy = padding + target_cell[1] * cell_size
            c_len = min(10, cell_size // 4)
            svg.append(
                f'<rect x="{sx}" y="{sy}" width="{cell_size}" height="{cell_size}" '
                f'fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 2" rx="3" filter="url(#reticle-glow)" />'
            )
            # Corner targeting brackets
            svg.append(f'<path d="M {sx+2} {sy+2+c_len} L {sx+2} {sy+2} L {sx+2+c_len} {sy+2}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')
            svg.append(f'<path d="M {sx+cell_size-2-c_len} {sy+2} L {sx+cell_size-2} {sy+2} L {sx+cell_size-2} {sy+2+c_len}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')
            svg.append(f'<path d="M {sx+2} {sy+cell_size-2-c_len} L {sx+2} {sy+cell_size-2} L {sx+2+c_len} {sy+cell_size-2}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')
            svg.append(f'<path d="M {sx+cell_size-2-c_len} {sy+cell_size-2} L {sx+cell_size-2} {sy+cell_size-2} L {sx+cell_size-2} {sy+cell_size-2-c_len}" fill="none" stroke="#38bdf8" stroke-width="2.5" />')

        # 4. Active Dropoff Badges (D1, D2...)
        for (dx, dy), d_lbls in active_dropoffs.items():
            cx = padding + dx * cell_size + cell_size / 2
            cy = padding + dy * cell_size + cell_size / 2
            d_str = "/".join(d_lbls)
            badge_w = max(28, len(d_str) * 8 + 10)
            badge_h = min(24, cell_size - 4)
            svg.append(
                f'<rect x="{cx - badge_w/2}" y="{cy - badge_h/2}" width="{badge_w}" height="{badge_h}" rx="4" '
                f'fill="#064e3b" stroke="#10b981" stroke-width="2" />'
            )
            svg.append(
                f'<text x="{cx}" y="{cy + 4}" fill="#a7f3d0" font-size="{font_sz}" font-weight="bold" text-anchor="middle">{d_str}</text>'
            )

        # 5. Pickups (P1, P2...) with full lifecycle:
        # - Unpicked: Blue badge (P1)
        # - Picked up / in transit: Amber badge (P1📦)
        # - Completed: Cleared from floor
        for idx, t in enumerate(snapshot.tasks, 1):
            if not t.pickup or t.pickup in shelves_set or t.pickup in custom_obs_set:
                continue
            if t.is_finished:
                continue
            cx = padding + t.pickup[0] * cell_size + cell_size / 2
            cy = padding + t.pickup[1] * cell_size + cell_size / 2
            badge_h = min(24, cell_size - 4)
            if t.is_picked_up:
                svg.append(
                    f'<rect x="{cx - 20}" y="{cy - badge_h/2}" width="40" height="{badge_h}" rx="4" '
                    f'fill="#78350f" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="3 2" opacity="0.85" />'
                )
                svg.append(
                    f'<text x="{cx}" y="{cy + 4}" fill="#fef3c7" font-size="{font_sz}" font-weight="bold" text-anchor="middle">P{idx}📦</text>'
                )
            else:
                svg.append(
                    f'<rect x="{cx - 16}" y="{cy - badge_h/2}" width="32" height="{badge_h}" rx="4" '
                    f'fill="#1e3a8a" stroke="#3b82f6" stroke-width="2" />'
                )
                svg.append(
                    f'<text x="{cx}" y="{cy + 4}" fill="#bfdbfe" font-size="{font_sz}" font-weight="bold" text-anchor="middle">P{idx}</text>'
                )

        # 6. Real Planned Paths (Distinct color per robot, reflecting r.path)
        for idx, r in enumerate(snapshot.robots):
            r_path = r.path
            if len(r_path) >= 1:
                full_pts = [r.position] + [p for p in r_path if p != r.position]
                if len(full_pts) >= 2:
                    color = ROBOT_PATH_COLORS[idx % len(ROBOT_PATH_COLORS)]
                    marker_id = f"path-arrow-{idx % len(ROBOT_PATH_COLORS)}"
                    pts = []
                    for px, py in full_pts:
                        cx = padding + px * cell_size + cell_size / 2
                        cy = padding + py * cell_size + cell_size / 2
                        pts.append(f"{cx},{cy}")

                    polyline_str = " ".join(pts)
                    svg.append(
                        f'<polyline points="{polyline_str}" fill="none" stroke="{color}" stroke-width="2.5" '
                        f'stroke-dasharray="6 3" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#{marker_id})" opacity="0.85" />'
                    )

        # 7. AMRs — render the authoritative simulator position only.
        for r in snapshot.robots:
            r_id = f"R{r.robot_id}" if r.robot_id is not None else "R?"
            st = (r.availability_state if r.availability_state not in {"", "UNKNOWN"}
                  else r.status).upper()
            is_conflicted = str(r.robot_id) in conflicted_robots or r.position in conflict_cells
            is_discharged = st == "DISCHARGED" or r.battery <= 0
            is_low_battery = not is_discharged and (r.battery <= 25.0 or st == "LOW_BATTERY") and st not in ("OFFLINE", "CHARGING")

            if is_conflicted:
                state_color = ROBOT_COLORS["CONFLICT"]
            elif is_discharged:
                state_color = ROBOT_COLORS["DISCHARGED"]
            elif is_low_battery:
                state_color = ROBOT_COLORS["LOW_BATTERY"]
            elif st == "WAITING":
                state_color = ROBOT_COLORS["WAITING"]
            elif st == "CHARGING":
                state_color = ROBOT_COLORS["CHARGING"]
            elif st == "MOVING":
                state_color = ROBOT_COLORS["MOVING"]
            else:
                state_color = ROBOT_COLORS.get(st, ROBOT_COLORS["IDLE"])

            cx = padding + r.position[0] * cell_size + cell_size / 2
            cy = padding + r.position[1] * cell_size + cell_size / 2
            r_radius = max(8, min(16, cell_size // 2 - 4))

            if is_conflicted:
                svg.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r_radius + 5}" fill="none" stroke="#ef4444" stroke-width="3" filter="url(#conflict-glow)" />'
                )
            elif is_low_battery:
                svg.append(
                    f'<circle cx="{cx}" cy="{cy}" r="{r_radius + 4}" fill="none" stroke="#ef4444" stroke-width="2" stroke-dasharray="3 2" />'
                )

            svg.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r_radius}" fill="{state_color}" stroke="#ffffff" stroke-width="2" />'
            )
            r_font_sz = max(8, min(11, r_radius))
            svg.append(
                f'<text x="{cx}" y="{cy + r_font_sz/2}" fill="#ffffff" font-size="{r_font_sz}" font-weight="bold" text-anchor="middle">{html.escape(r_id)}</text>'
            )

            # Package indicator comes from the normalized simulator snapshot.
            if getattr(r, "has_package", False):
                pkg_sz = max(10, min(14, cell_size // 3))
                svg.append(
                    f'<rect x="{cx + r_radius - 6}" y="{cy - r_radius - 2}" width="{pkg_sz}" height="{pkg_sz}" rx="2" fill="#f59e0b" stroke="#b45309" stroke-width="1.5" />'
                )
                svg.append(
                    f'<text x="{cx + r_radius}" y="{cy - r_radius + pkg_sz - 4}" fill="#78350f" font-size="8" font-weight="bold" text-anchor="middle">📦</text>'
                )

            # Charging / Low Battery badge
            if st == "CHARGING":
                svg.append(
                    f'<text x="{cx}" y="{cy - r_radius - 4}" fill="#60a5fa" font-size="10" font-weight="bold" text-anchor="middle">⚡</text>'
                )
            elif is_low_battery:
                svg.append(
                    f'<text x="{cx}" y="{cy - r_radius - 4}" fill="#f87171" font-size="10" font-weight="bold" text-anchor="middle">🪫</text>'
                )

        svg.append('</svg>')
        return "\n".join(svg)
