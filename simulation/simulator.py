from planning.collision import CollisionDetector
from planning.deadlock import DeadlockDetector
from communication.message import Message, MessageType


class Simulator:
    def __init__(
        self,
        warehouse,
        robots,
        network,
        reservation_table,
        metrics,
        auction=None,
        dt=0.1,
        orca_enabled=False,
    ):
        self.warehouse = warehouse
        self.robots = list(robots)
        self.network = network

        self.reservation_table = reservation_table
        self.metrics = metrics
        self.auction = auction

        self.dt = dt
        self.orca_enabled = orca_enabled
        self.time = 0.0

        self.collision_detector = CollisionDetector()
        self.deadlock_detector = DeadlockDetector()

        # Deadlock cycle signatures that have already been counted.
        #
        # This prevents:
        #
        #     same cycle detected at t=1
        #     same cycle detected at t=2
        #     same cycle detected at t=3
        #
        # from being reported as three different deadlocks.
        self._counted_deadlock_cycles = set()

    # ------------------------------------------------------------------
    # MAIN SIMULATION STEP
    # ------------------------------------------------------------------

    def step(self):
        timestep = round(
            self.time / self.dt
        )

        # Remove expired reservations.
        self.reservation_table.release_expired(
            timestep
        )

        # Synchronize robot clocks.
        for robot in self.robots:
            robot.set_time(timestep)
            robot.orca_enabled = self.orca_enabled

        # --------------------------------------------------------------
        # ROBOT UPDATE
        # --------------------------------------------------------------

        for robot in sorted(
            self.robots,
            key=lambda item: (
                -item.calculate_priority(),
                item.robot_id,
            ),
        ):
            robot.update()

        # --------------------------------------------------------------
        # MOVEMENT / LOCAL CONFLICT HANDLING
        # --------------------------------------------------------------

        for robot in self.robots:
            result = robot.prepare_orca(self.robots, self.dt)
            if result is not None:
                self.metrics.record_orca(result, robot._orca_preferred_velocity, robot._orca_target is not None)

        for robot in self.robots:
            if robot.detect_conflict():
                robot.handle_conflict(
                    self.dt
                )
            else:
                if robot.move():
                    self.metrics.record_movement(
                        robot,
                        1.0,
                    )

        # --------------------------------------------------------------
        # PHYSICAL COLLISION CHECK
        # --------------------------------------------------------------

        collisions = (
            self.collision_detector.detect_all_collisions(
                self.robots
            )
        )

        for a, b in collisions:
            self.metrics.record_collision(
                a,
                b,
            )

        # --------------------------------------------------------------
        # FUTURE PATH CONFLICT CHECK
        # --------------------------------------------------------------

        path_conflicts = (
            self.collision_detector.detect_all_path_conflicts(
                self.robots
            )
        )

        for a, b in path_conflicts:
            if (a, b) not in collisions and (
                b,
                a,
            ) not in collisions:
                a.handle_conflict(
                    self.dt
                )
                b.handle_conflict(
                    self.dt
                )

        # --------------------------------------------------------------
        # TASK COMPLETION
        # --------------------------------------------------------------

        for robot in self.robots:
            if robot.is_task_complete():
                task = robot.tasks[
                    robot.state.current_task_id
                ]

                robot.complete_task()

                self.metrics.record_task_completed(
                    task,
                    robot,
                )

        # --------------------------------------------------------------
        # DEADLOCK DETECTION / RECOVERY
        # --------------------------------------------------------------

        deadlock = (
            self.deadlock_detector.detect_deadlocks(
                self.robots
            )
        )

        if deadlock["detected"]:
            cycle_key = tuple(
                sorted(
                    deadlock["robots"]
                )
            )

            # Count each currently identified cycle only once.
            if (
                cycle_key
                not in self._counted_deadlock_cycles
            ):
                self._counted_deadlock_cycles.add(
                    cycle_key
                )

                self.metrics.record_deadlock(
                    self.robots
                )

            # Attempt recovery.
            self.deadlock_detector.resolve_deadlock(
                self.robots
            )

        self.time += self.dt

    # ------------------------------------------------------------------
    # NORMAL RUN
    # ------------------------------------------------------------------

    def run(self, steps=1000):
        self.metrics.start_simulation(
            self.time
        )

        for _ in range(steps):
            if self.is_finished():
                break

            self.step()

        self.metrics.end_simulation(
            self.time
        )

        return self.metrics.get_summary()

    # ------------------------------------------------------------------
    # STOP-AND-WAIT BASELINE
    # ------------------------------------------------------------------

    def run_stop_and_wait(self, steps=1000):
        """
        Reference execution that advances only one robot per timestep.
        """

        self.metrics.start_simulation(
            self.time
        )

        for _ in range(steps):
            if self.is_finished():
                break

            for robot in self.robots:
                robot.update()

                if (
                    robot.state.current_task_id
                    is not None
                    and robot.state.get_next_position()
                    is None
                ):
                    robot.plan_path()

                if robot.move():
                    self.metrics.record_movement(
                        robot,
                        1.0,
                    )

                if robot.is_task_complete():
                    task = robot.tasks[
                        robot.state.current_task_id
                    ]

                    robot.complete_task()

                    self.metrics.record_task_completed(
                        task,
                        robot,
                    )

                self.time += self.dt

        self.metrics.end_simulation(
            self.time
        )

        return self.metrics.get_summary()

    # ------------------------------------------------------------------
    # TASK / OBSTACLE MANAGEMENT
    # ------------------------------------------------------------------

    def spawn_task(self, task):
        self.warehouse.add_task(task)

    def spawn_obstacle(self, position):
        self.warehouse.add_obstacle(
            position
        )

        for robot in self.robots:
            robot.network.broadcast(
                -1,
                Message(
                    -1,
                    MessageType.OBSTACLE,
                    self.time,
                    {
                        "position": tuple(
                            position
                        )
                    },
                ),
            )

    def remove_obstacle(self, position):
        self.warehouse.remove_obstacle(
            position
        )

    # ------------------------------------------------------------------
    # SIMULATION STATE
    # ------------------------------------------------------------------

    def is_finished(self):
        return all(
            task.status.value == "COMPLETED"
            for task in self.warehouse.tasks.values()
        )

    def reset(self):
        self.time = 0.0

        self.metrics.__init__()

        self.reservation_table._reservations.clear()

        for robot in self.robots:
            robot._orca_target = None
            robot._orca_result = None
            robot.state.velocity = (0, 0)

        # Reset deadlock bookkeeping.
        self._counted_deadlock_cycles.clear()
        self.deadlock_detector.resolved_cycles.clear()
