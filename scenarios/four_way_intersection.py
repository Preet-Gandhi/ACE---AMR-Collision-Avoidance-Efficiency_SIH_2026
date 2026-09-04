from .reservation_helpers import build_world


def build():
    simulator, robots = build_world(starts=((4, 0), (0, 4), (4, 8), (8, 4)))
    paths = [[(4, 0), (4, 1), (4, 2), (4, 3), (4, 4)], [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4)], [(4, 8), (4, 7), (4, 6), (4, 5), (4, 4)], [(8, 4), (7, 4), (6, 4), (5, 4), (4, 4)]]
    return simulator, robots, paths
