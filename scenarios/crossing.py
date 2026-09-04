from .reservation_helpers import build_world


def build():
    # Both routes approach the center cell (4, 4) at the same timestep.
    simulator, robots = build_world(starts=((4, 0), (4, 8)))
    return simulator, robots, [[(4, 0), (4, 1), (4, 2), (4, 3), (4, 4)], [(4, 8), (4, 7), (4, 6), (4, 5), (4, 4)]]
