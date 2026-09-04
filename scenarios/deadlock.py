from auction.task import Task

from .reservation_helpers import build_world


def build():
    """Three-robot workload for deadlock recovery."""

    simulator, robots = build_world(
        size=(7, 7),
        starts=(
            (0, (1, 1)),
            (1, (5, 1)),
            (2, (5, 5)),
        ),
    )

    tasks = [
        Task(
            1,
            (1, 1),
            (6, 6),
            priority=3,
        ),
        Task(
            2,
            (5, 1),
            (1, 5),
            priority=2,
        ),
        Task(
            3,
            (5, 5),
            (1, 1),
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

    return simulator, robots


def seed_cycle(simulator, robots):
    """Create deterministic R0 -> R1 -> R2 -> R0 cycle."""

    paths = [
        [
            (1, 1),
            (2, 1),
        ],
        [
            (5, 1),
            (5, 2),
        ],
        [
            (5, 5),
            (4, 5),
        ],
    ]

    table = simulator.reservation_table

    # R1 waits for R0.
    table.reserve(
        1,
        paths[0][-1],
        1,
    )

    # R2 waits for R1.
    table.reserve(
        2,
        paths[1][-1],
        1,
    )

    # R0 waits for R2.
    table.reserve(
        0,
        paths[2][-1],
        1,
    )

    for robot, path in zip(
        robots,
        paths,
    ):
        robot.current_time = 0

        robot.state.set_path(
            path[1:]
        )

        robot.state.status = "WAITING"

    return paths