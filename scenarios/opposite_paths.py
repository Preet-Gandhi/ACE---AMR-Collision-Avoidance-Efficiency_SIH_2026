from .reservation_helpers import build_world


def build():
    simulator, robots = build_world(starts=((0, (3, 4)), (1, (5, 4))))
    return simulator, robots, [[(3, 4), (4, 4), (5, 4)], [(5, 4), (4, 4), (3, 4)]]
