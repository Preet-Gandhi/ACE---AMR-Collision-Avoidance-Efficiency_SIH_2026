from .reservation_helpers import build_world


def build():
    simulator, robots = build_world(starts=((0, (0, 0)), (1, (2, 0)), (2, (1, 1))))
    paths = [[(1, 0)], [(2, 1)], [(0, 0)]]
    for index, path in enumerate(paths):
        robots[index].state.path = path
        robots[index].state.path_index = 0
        robots[index].state.status = "WAITING"
    simulator.reservation_table.reserve(1, (1, 0), 1)
    simulator.reservation_table.reserve(2, (2, 1), 1)
    simulator.reservation_table.reserve(0, (0, 0), 1)
    return simulator, robots, paths
