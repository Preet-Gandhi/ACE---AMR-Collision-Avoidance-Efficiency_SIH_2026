from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
from dashboard.snapshot import NormalizedSnapshot


class GridRenderer:
    """Renders the 2D warehouse grid with robots, obstacles, reservations, paths, and conflicts."""

    @staticmethod
    def render(snapshot: NormalizedSnapshot, color: bool = False) -> str:
        width, height = snapshot.grid_size

        # ANSI color codes
        C_RESET = "\033[0m" if color else ""
        C_ROBOT_NORM = "\033[92m" if color else ""       # Green
        C_ROBOT_WAIT = "\033[93m" if color else ""       # Yellow
        C_ROBOT_CONF = "\033[91m" if color else ""       # Red
        C_OBSTACLE = "\033[90m" if color else ""         # Dark gray
        C_RESERVE = "\033[94m" if color else ""          # Blue
        C_PATH = "\033[96m" if color else ""             # Cyan
        C_CONFLICT = "\033[1;91m" if color else ""       # Bold Red

        # Identify conflicts and conflicted robots
        conflict_cells: Set[Tuple[int, int]] = set()
        conflicted_robots: Set[str] = set()
        for c in snapshot.conflicts:
            if c.location:
                conflict_cells.add(c.location)
            for r in c.robots:
                conflicted_robots.add(str(r))

        # Map robot positions
        robot_positions: Dict[Tuple[int, int], List[Tuple[str, str, str]]] = {}
        for r in snapshot.robots:
            pos = r.position
            label = f"R{r.robot_id}" if r.robot_id is not None else "R?"
            status = r.status.upper() if r.status else "UNKNOWN"
            is_conflicted = str(r.robot_id) in conflicted_robots or pos in conflict_cells
            robot_positions.setdefault(pos, []).append((label, status, "CONFLICT" if is_conflicted else status))

        obstacles: Set[Tuple[int, int]] = set(snapshot.obstacles)

        # Reservations
        reservation_cells: Dict[Tuple[int, int], List[str]] = {}
        for res in snapshot.reservations:
            res_label = f"~{res.robot_id}" if res.robot_id is not None else "~"
            reservation_cells.setdefault(res.position, []).append(res_label)

        # Directional planned paths
        path_arrows: Dict[Tuple[int, int], str] = {}
        for r_id, path in snapshot.paths.items():
            for i in range(len(path)):
                pt = path[i]
                if i < len(path) - 1:
                    nxt = path[i + 1]
                    dx, dy = nxt[0] - pt[0], nxt[1] - pt[1]
                    if dx > 0:
                        symbol = ">"
                    elif dx < 0:
                        symbol = "<"
                    elif dy > 0:
                        symbol = "v"
                    elif dy < 0:
                        symbol = "^"
                    else:
                        symbol = "*"
                else:
                    symbol = "*"
                if pt not in path_arrows:
                    path_arrows[pt] = symbol

        lines: List[str] = []
        lines.append(f"Warehouse Grid ({width}x{height}):")

        cell_w = 4
        header_pad = "    "
        header_cols = "".join(f"{x:>{cell_w}}" for x in range(width))
        lines.append(header_pad + header_cols)
        lines.append(header_pad + "-" * (width * cell_w))

        for y in range(height):
            row_cells: List[str] = []
            for x in range(width):
                pos = (x, y)
                if pos in robot_positions:
                    robs = robot_positions[pos]
                    label, _, state = robs[0]
                    if state == "CONFLICT":
                        disp_str = f"!{label}" if len(label) <= 2 else f"!{label[:2]}"
                        colored_cell = f"{C_ROBOT_CONF}{disp_str:>{cell_w}}{C_RESET}"
                    elif state == "WAITING":
                        colored_cell = f"{C_ROBOT_WAIT}{label:>{cell_w}}{C_RESET}"
                    else:
                        colored_cell = f"{C_ROBOT_NORM}{label:>{cell_w}}{C_RESET}"
                    row_cells.append(colored_cell)
                elif pos in conflict_cells:
                    colored_cell = f"{C_CONFLICT}{'!':>{cell_w}}{C_RESET}"
                    row_cells.append(colored_cell)
                elif pos in obstacles:
                    colored_cell = f"{C_OBSTACLE}{'#':>{cell_w}}{C_RESET}"
                    row_cells.append(colored_cell)
                elif pos in reservation_cells:
                    # Distinguishable reservation cell
                    colored_cell = f"{C_RESERVE}{'~':>{cell_w}}{C_RESET}"
                    row_cells.append(colored_cell)
                elif pos in path_arrows:
                    # Planned path
                    symbol = path_arrows[pos]
                    colored_cell = f"{C_PATH}{symbol:>{cell_w}}{C_RESET}"
                    row_cells.append(colored_cell)
                else:
                    row_cells.append(f"{'.':>{cell_w}}")

            lines.append(f"{y:>3} |" + "".join(row_cells))

        lines.append("")
        legend_items = [
            f"{C_ROBOT_NORM}[R#]{C_RESET} Robot",
            f"{C_OBSTACLE}[#]{C_RESET} Blocked/Obstacle",
            f"{C_RESERVE}[~]{C_RESET} Reservation",
            f"{C_PATH}[*/>/v]{C_RESET} Planned Path",
            f"{C_CONFLICT}[!]{C_RESET} Conflict",
            "[.] Empty",
        ]
        lines.append("Grid Legend: " + "  |  ".join(legend_items))
        return "\n".join(lines)
