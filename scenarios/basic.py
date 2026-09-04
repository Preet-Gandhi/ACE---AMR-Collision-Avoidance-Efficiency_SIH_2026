from .reservation_helpers import build_world


def build():
    return build_world(starts=((0, (0, 0)), (1, (8, 8))))
