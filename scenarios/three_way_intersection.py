from auction.task import Task

from .reservation_helpers import build_world


def build():
    """Three-way intersection workload."""

    simulator, robots = build_world(
        size=(9, 9),
        starts=(
            (0, (4, 1)),
            (1, (1, 7)),
            (2, (7, 7)),
        ),
    )

    tasks = [
        Task(
            10,
            (4, 1),
            (7, 7),
            priority=3,
        ),
        Task(
            11,
            (1, 7),
            (4, 1),
            priority=2,
        ),
        Task(
            12,
            (7, 7),
            (1, 7),
            priority=1,
        ),
    ]

    for task, robot in zip(
        tasks,
        robots,
    ):
        simulator.warehouse.add_task(
            task
        )

        task.assign(
            robot.robot_id
        )

        robot.accept_task(
            task
        )

    # Routes all pass through the central
    # intersection.
    paths = [
        [
            (4, 1),
            (4, 2),
            (4, 3),
            (4, 4),
            (5, 4),
            (6, 4),
            (7, 4),
            (7, 5),
            (7, 6),
            (7, 7),
        ],
        [
            (1, 7),
            (2, 7),
            (3, 7),
            (4, 7),
            (4, 6),
            (4, 5),
            (4, 4),
            (4, 3),
            (4, 2),
            (4, 1),
        ],
        [
            (7, 7),
            (6, 7),
            (5, 7),
            (4, 7),
            (3, 7),
            (2, 7),
            (1, 7),
        ],
    ]

    return simulator, robots, paths