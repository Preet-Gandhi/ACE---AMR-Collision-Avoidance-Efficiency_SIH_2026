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
        self._active_collision_pairs = set()

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
        self.reservation_table.release_expired_leases(timestep)

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

        # Atomic occupancy guard. Process one robot at a time in priority
        # order. Robots that have not yet been processed still occupy their
        # old cells; once a robot successfully moves, its old cell is free and
        # a following robot may enter it on the same tick. This prevents
        # overlap without introducing a permanent one-cell-following deadlock.
        movement_order = sorted(
            [robot for robot in self.robots if robot.is_online()],
            key=lambda item: (-item.calculate_priority(), item.robot_id),
        )
        positions_before = {robot.robot_id: tuple(robot.state.position) for robot in self.robots}
        unmoved_ids = {robot.robot_id for robot in movement_order}
        offline_positions = {
            tuple(robot.state.position)
            for robot in self.robots
            if not robot.is_online()
        }

        for robot in movement_order:
            before_replans = getattr(robot, "replan_count", 0)
            blocked_positions = {
                positions_before[rid]
                for rid in unmoved_ids
                if rid != robot.robot_id
            }
            blocked_positions.update(offline_positions - {tuple(robot.state.position)})
            moved = False
            if robot.detect_conflict():
                robot.handle_conflict(self.dt)
                self.metrics.record_wait(robot, self.dt)
            else:
                moved = robot.move(blocked_positions=blocked_positions)
                if moved:
                    self.metrics.record_movement(robot, 1.0)
                else:
                    self.metrics.record_wait(robot, self.dt)

            # Only remove the robot from the occupancy guard if it actually
            # vacated its old cell. A robot that was denied movement remains
            # physically present and must continue blocking that cell.
            if moved:
                unmoved_ids.discard(robot.robot_id)
            if getattr(robot, "replan_count", 0) > before_replans:
                self.metrics.replanning_count += getattr(robot, "replan_count", 0) - before_replans

        # --------------------------------------------------------------
        # PHYSICAL COLLISION CHECK
        # --------------------------------------------------------------

        collisions = (
            self.collision_detector.detect_all_collisions(
                self.robots
            )
        )

        # Count a physical overlap once per robot pair, not once per frame.
        current_collision_pairs = {tuple(sorted((a.robot_id, b.robot_id))) for a, b in collisions}
        for pair in current_collision_pairs - self._active_collision_pairs:
            a = next(r for r in self.robots if r.robot_id == pair[0])
            b = next(r for r in self.robots if r.robot_id == pair[1])
            self.metrics.record_collision(a, b)
        self._active_collision_pairs = current_collision_pairs

        # --------------------------------------------------------------
        # FUTURE PATH CONFLICT CHECK
        # --------------------------------------------------------------
        # Do not stop robots merely because their geometric paths intersect.
        # The reservation table is time-indexed and already decides whether
        # the two robots can occupy the same vertex/edge at the same tick.
        # Treating every geometric intersection as a live conflict creates
        # false deadlocks and was the main source of the old simulation
        # freezing on shared aisles.
        path_conflicts = self.collision_detector.detect_all_path_conflicts(self.robots)

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
        if self.auction is not None:
            if any(getattr(robot, "distributed", False) for robot in self.robots):
                self.auction.start_distributed(task)
            else:
                self.auction.run_auction(task, verbose=False)

    def spawn_obstacle(self, position):
        self.warehouse.add_obstacle(
            position
        )
        self.network.broadcast(
            -1,
            Message(-1, MessageType.OBSTACLE, self.time, {"position": tuple(position), "source": "simulator"}),
        )

    def remove_obstacle(self, position):
        self.warehouse.remove_obstacle(
            position
        )
        self.network.broadcast(
            -1,
            Message(-1, MessageType.OBSTACLE_CLEARED, self.time, {"position": tuple(position), "source": "simulator"}),
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
        self.reservation_table._edge_reservations.clear()
        self.reservation_table._leases.clear()
        self.reservation_table._edge_leases.clear()

        for robot in self.robots:
            robot.state.battery = robot.initial_battery
            robot.state.online = True
            robot.state.availability_state = "ONLINE"
            robot.state.status = "IDLE"
            robot.state.current_task_id = None
            robot.state.carrying_package = False
            robot.state.clear_path()
            self.reservation_table.register_priority(robot.robot_id, 0)
            robot.waiting_time = 0.0
            robot.blockage_waiting = 0.0
            robot.replan_count = 0
            robot.pending_reservations.clear()
            robot.reservation_leases.clear()
            robot.last_plan_reserved = False
            robot._orca_target = None
            robot._orca_result = None
            robot.state.velocity = (0, 0)

        # Reset deadlock bookkeeping.
        self._counted_deadlock_cycles.clear()
        self.deadlock_detector.resolved_cycles.clear()
