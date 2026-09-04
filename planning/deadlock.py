"""Deadlock detection and recovery for reservation-based AMR planning."""

from __future__ import annotations


class DeadlockDetector:
    """
    Detect and resolve cyclic waiting between AMRs.

    A directed edge:

        A -> B

    means robot A is waiting for a reservation currently owned
    by robot B.

    A cycle such as:

        A -> B -> C -> A

    represents a deadlock.
    """

    def __init__(self):
        # Remember cycles that have already been resolved.
        #
        # This prevents the same persistent cycle from being
        # counted/resolved repeatedly on every simulation tick.
        self.resolved_cycles = set()

    # ------------------------------------------------------------------
    # WAIT-FOR GRAPH
    # ------------------------------------------------------------------

    def build_wait_graph(self, robots):
        """
        Build a wait-for graph.

        Returns:

            {
                robot_id: {blocking_robot_ids}
            }
        """

        robots = list(robots)
        robots = [robot for robot in robots if robot.is_online()]

        graph = {
            robot.robot_id: set()
            for robot in robots
        }

        known_ids = set(graph)

        for robot in robots:
            if getattr(robot.state, "status", None) != "WAITING":
                continue

            next_position = robot.state.get_next_position()

            if next_position is None:
                continue

            start_time = getattr(
                robot,
                "current_time",
                0,
            ) + 1

            owner = robot.reservation_table.get_owner(
                next_position,
                start_time,
            )

            if owner in known_ids and owner != robot.robot_id:
                graph[robot.robot_id].add(owner)

            # Reservations are not the only source of blocking. A parked or
            # waiting AMR can physically occupy the requested cell after its
            # future reservations have expired/released. Include that owner
            # in the wait-for graph so occupancy-induced cycles are visible.
            for other in robots:
                if other.robot_id == robot.robot_id:
                    continue
                if tuple(other.state.position) == tuple(next_position):
                    graph[robot.robot_id].add(other.robot_id)
                    break

            # Also account for a reserved head-on edge. The vertex may be
            # free while the opposite directed edge is already claimed.
            previous = tuple(robot.state.position)
            edge_owner = robot.reservation_table.get_edge_owner(
                previous, next_position, start_time
            )
            reverse_owner = robot.reservation_table.get_edge_owner(
                next_position, previous, start_time
            )
            for edge_blocker in (edge_owner, reverse_owner):
                if edge_blocker in known_ids and edge_blocker != robot.robot_id:
                    graph[robot.robot_id].add(edge_blocker)

        return graph

    # ------------------------------------------------------------------
    # CYCLE DETECTION
    # ------------------------------------------------------------------

    def detect_cycle(self, graph):
        """
        Return True if the wait-for graph contains a cycle.
        """

        visiting = set()
        visited = set()

        def visit(node):
            if node in visiting:
                return True

            if node in visited:
                return False

            visiting.add(node)

            for neighbour in graph.get(node, ()):
                if visit(neighbour):
                    return True

            visiting.remove(node)
            visited.add(node)

            return False

        return any(
            visit(node)
            for node in graph
        )

    def _cycle_nodes(self, graph):
        """
        Return all robot IDs participating in directed cycles.
        """

        nodes = set()

        def reaches(start, target):
            stack = [start]
            seen = set()

            while stack:
                node = stack.pop()

                if node == target:
                    return True

                if node in seen:
                    continue

                seen.add(node)

                stack.extend(
                    graph.get(node, ())
                )

            return False

        # An edge source -> target belongs to a cycle if target
        # can eventually reach source.
        for source, targets in graph.items():
            for target in targets:
                if reaches(target, source):
                    nodes.add(source)
                    nodes.add(target)

        return nodes

    def _cycle_key(self, cycle_nodes):
        """
        Create a deterministic identifier for a deadlock cycle.
        """

        return tuple(sorted(cycle_nodes))

    # ------------------------------------------------------------------
    # DETECTION
    # ------------------------------------------------------------------

    def detect_deadlocks(self, robots):
        """
        Return structured deadlock information.

        Result:

            {
                "detected": bool,
                "robots": list[int],
                "rerouted_robot_id": int | None
            }
        """

        robots = list(robots)

        graph = self.build_wait_graph(robots)

        cycle_nodes = self._cycle_nodes(graph)

        return {
            "detected": bool(cycle_nodes),
            "robots": sorted(cycle_nodes),
            "rerouted_robot_id": None,
        }

    # ------------------------------------------------------------------
    # ROBOT SELECTION
    # ------------------------------------------------------------------

    def select_robot_to_reroute(self, robots):
        """
        Select exactly ONE robot participating in the cycle.

        The lowest-priority robot yields.

        Robot ID is used as a deterministic tie breaker.
        """

        robots = list(robots)

        if not robots:
            return None

        graph = self.build_wait_graph(robots)

        cycle_ids = self._cycle_nodes(graph)

        candidates = [
            robot
            for robot in robots
            if robot.robot_id in cycle_ids
        ]

        if not candidates:
            return None

        def priority(robot):
            try:
                return float(
                    robot.calculate_priority()
                )
            except (
                AttributeError,
                TypeError,
                ValueError,
            ):
                return float(
                    getattr(
                        robot,
                        "last_priority",
                        0.0,
                    )
                )

        return min(
            candidates,
            key=lambda robot: (
                priority(robot),
                robot.robot_id,
            ),
        )

    # ------------------------------------------------------------------
    # TEMPORARY ESCAPE CELLS
    # ------------------------------------------------------------------

    def _get_escape_blocked_cells(
        self,
        selected_robot,
        deadlocked_robots,
    ):
        """
        Build temporary blocked cells for the selected robot.

        We block the positions and immediate next positions of the
        other robots participating in the cycle.

        This is temporary planning information only.

        It does NOT modify the warehouse itself.
        """

        blocked = set()

        for robot in deadlocked_robots:
            if robot.robot_id == selected_robot.robot_id:
                continue

            position = getattr(
                robot.state,
                "position",
                None,
            )

            if position is not None:
                blocked.add(tuple(position))

            next_position = robot.state.get_next_position()

            if next_position is not None:
                blocked.add(tuple(next_position))

        # Never block the selected robot's current position.
        selected_position = getattr(
            selected_robot.state,
            "position",
            None,
        )

        if selected_position is not None:
            blocked.discard(
                tuple(selected_position)
            )

        return blocked

    # ------------------------------------------------------------------
    # RECOVERY
    # ------------------------------------------------------------------

    def resolve_deadlock(self, robots):
        """
        Resolve one detected deadlock.

        Recovery procedure:

            1. Detect cycle.
            2. Select exactly one robot.
            3. Release that robot's reservations.
            4. Clear its old path.
            5. Temporarily block contested cells.
            6. Force a new route.
            7. Return structured result.
        """

        robots = list(robots)

        detected = self.detect_deadlocks(robots)

        if not detected["detected"]:
            return detected

        cycle_ids = tuple(detected["robots"])

        cycle_key = self._cycle_key(cycle_ids)

        robot = self.select_robot_to_reroute(robots)

        if robot is None:
            return detected

        # Only ONE robot yields.
        blocked = self._get_escape_blocked_cells(
            robot,
            [
                candidate
                for candidate in robots
                if candidate.robot_id in cycle_ids
            ],
        )

        # Release the selected robot's reservations.
        robot.release_reservation()

        # Remove its old path.
        robot.state.clear_path()

        # Reset waiting counters so the robot gets a clean chance
        # to escape instead of immediately being treated as blocked.
        if hasattr(robot, "waiting_time"):
            robot.waiting_time = 0.0

        if hasattr(robot, "blockage_waiting"):
            robot.blockage_waiting = 0.0

        # Mark it as waiting while the new route is being generated.
        robot.state.status = "WAITING"

        new_path = []

        # --------------------------------------------------------------
        # IMPORTANT:
        #
        # Use the planner directly so we can pass temporary blocked
        # cells. Robot.plan_path() does not currently expose "blocked".
        # --------------------------------------------------------------

        try:
            if robot.state.current_task_id is not None:
                task = robot.tasks[
                    robot.state.current_task_id
                ]

                # Preserve the task phase during recovery. A loaded robot
                # must escape toward its delivery bay, not back to pickup.
                goal = task.dropoff if robot.state.carrying_package else task.pickup

                new_path = robot.planner.find_path(
                    robot.state.position,
                    goal,
                    robot.reservation_table,
                    robot.current_time,
                    blocked=blocked,
                    robot_id=robot.robot_id,
                )

                if new_path:
                    priority = robot.calculate_priority()

                    reserved = (
                        robot.reservation_table.reserve_path(
                            robot.robot_id,
                            new_path,
                            robot.current_time,
                            priority,
                        )
                    )

                    if reserved:
                        robot.last_plan_reserved = True
                        robot.state.set_path(
                            new_path[1:]
                        )

                        robot.state.status = "MOVING"

                    else:
                        new_path = []

        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            new_path = []

        # Record the cycle after recovery attempt. Releasing the selected
        # robot's reservations breaks the original wait-for cycle even if no
        # alternate route exists immediately.
        self.resolved_cycles.add(cycle_key)

        return {
            "detected": True,
            "robots": detected["robots"],
            "rerouted_robot_id": robot.robot_id,
            "rerouted": bool(new_path),
            "new_path": new_path,
            "blocked_cells": sorted(blocked),
            "cycle_key": cycle_key,
        }

    # ------------------------------------------------------------------
    # HELPER
    # ------------------------------------------------------------------

    def was_cycle_resolved(self, robots):
        """
        Check whether the currently detected cycle has already been
        handled.
        """

        result = self.detect_deadlocks(robots)

        if not result["detected"]:
            return False

        key = self._cycle_key(
            result["robots"]
        )

        return key in self.resolved_cycles
