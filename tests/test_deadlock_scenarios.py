import unittest

from planning.deadlock import DeadlockDetector
from scenarios.deadlock import build


class DeadlockScenarioTests(unittest.TestCase):

    def test_cycle_is_detected_and_one_robot_is_rerouted(self):
        simulator, robots, _ = build()

        detector = DeadlockDetector()

        result = detector.detect_deadlocks(
            robots
        )

        self.assertTrue(
            result["detected"]
        )

        self.assertEqual(
            set(result["robots"]),
            {0, 1, 2},
        )

        resolved = detector.resolve_deadlock(
            robots
        )

        self.assertTrue(
            resolved["detected"]
        )

        self.assertIn(
            resolved["rerouted_robot_id"],
            {0, 1, 2},
        )

    def test_deadlock_cycle_contains_all_three_robots(self):
        simulator, robots, _ = build()

        detector = DeadlockDetector()

        graph = detector.build_wait_graph(
            robots
        )

        self.assertEqual(
            graph[0],
            {1},
        )

        self.assertEqual(
            graph[1],
            {2},
        )

        self.assertEqual(
            graph[2],
            {0},
        )

        self.assertTrue(
            detector.detect_cycle(graph)
        )

    def test_exactly_one_lowest_priority_robot_is_selected(self):
        simulator, robots, _ = build()

        detector = DeadlockDetector()

        selected = (
            detector.select_robot_to_reroute(
                robots
            )
        )

        self.assertIsNotNone(
            selected
        )

        priorities = {
            robot.robot_id: robot.calculate_priority()
            for robot in robots
        }

        expected_id = min(
            priorities,
            key=lambda robot_id: (
                priorities[robot_id],
                robot_id,
            ),
        )

        self.assertEqual(
            selected.robot_id,
            expected_id,
        )

    def test_resolution_returns_structured_result(self):
        simulator, robots, _ = build()

        detector = DeadlockDetector()

        result = detector.resolve_deadlock(
            robots
        )

        self.assertIn(
            "detected",
            result,
        )

        self.assertIn(
            "robots",
            result,
        )

        self.assertIn(
            "rerouted_robot_id",
            result,
        )

        self.assertIn(
            "rerouted",
            result,
        )

        self.assertIn(
            "new_path",
            result,
        )

    def test_deadlock_is_actually_resolved(self):
        """
        The important behavior:

            cycle exists
                 ↓
            resolve it
                 ↓
            cycle disappears

        A deadlock-free system should NOT continue reporting
        the same cycle after successful recovery.
        """

        simulator, robots, _ = build()

        detector = DeadlockDetector()

        # Initial state MUST contain a deadlock.
        first_detection = (
            detector.detect_deadlocks(
                robots
            )
        )

        self.assertTrue(
            first_detection["detected"]
        )

        self.assertEqual(
            set(first_detection["robots"]),
            {0, 1, 2},
        )

        # Resolve the deadlock.
        resolution = (
            detector.resolve_deadlock(
                robots
            )
        )

        self.assertTrue(
            resolution["detected"]
        )

        self.assertIsNotNone(
            resolution["rerouted_robot_id"]
        )

        # The important assertion:
        #
        # After recovery, the original cycle should no longer exist.
        second_detection = (
            detector.detect_deadlocks(
                robots
            )
        )

        self.assertFalse(
            second_detection["detected"]
        )

        self.assertEqual(
            second_detection["robots"],
            [],
        )

    def test_resolved_cycle_is_recorded_once(self):
        """
        Verify that a resolved cycle is remembered once and
        does not create duplicate bookkeeping entries.
        """

        simulator, robots, _ = build()

        detector = DeadlockDetector()

        first_detection = (
            detector.detect_deadlocks(
                robots
            )
        )

        self.assertTrue(
            first_detection["detected"]
        )

        cycle_key = tuple(
            sorted(
                first_detection["robots"]
            )
        )

        resolution = (
            detector.resolve_deadlock(
                robots
            )
        )

        self.assertEqual(
            resolution["cycle_key"],
            cycle_key,
        )

        self.assertIn(
            cycle_key,
            detector.resolved_cycles,
        )

        # The deadlock has been resolved, so a second
        # detection should correctly report NO cycle.
        second_detection = (
            detector.detect_deadlocks(
                robots
            )
        )

        self.assertFalse(
            second_detection["detected"]
        )

        # Only one cycle should have been recorded.
        self.assertEqual(
            len(detector.resolved_cycles),
            1,
        )


if __name__ == "__main__":
    unittest.main()