from .reservation_helpers import build_world


def build():
    simulator, robots = build_world(starts=((0, (4, 2)), (1, (2, 4)), (2, (6, 4))))
    paths = [[(4, 3), (4, 4)], [(3, 4), (4, 4)], [(5, 4), (4, 4)]]
    return simulator, robots, paths
