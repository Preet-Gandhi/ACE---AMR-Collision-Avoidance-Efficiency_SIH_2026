import unittest

from planning.deadlock import DeadlockDetector
from scenarios.deadlock import build as build_deadlock
from scenarios.deadlock import seed_cycle


class DeadlockScenarioTests(unittest.TestCase):

    def setUp(self):
        self.detector = DeadlockDetector()

    def test_wait_graph_detects_three_way_cycle(self):
        simulator, robots = build_deadlock()

        seed_cycle(
            simulator,
            robots,
        )

        graph = self.detector.build_wait_graph(
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

        result = self.detector.detect_deadlocks(
            robots
        )

        self.assertTrue(
            result["detected"]
        )

        self.assertEqual(
            result["robots"],
            [0, 1, 2],
        )

        self.assertIsNone(
            result["rerouted_robot_id"]
        )

    def test_exactly_one_lowest_priority_robot_is_selected(self):
        simulator, robots = build_deadlock()

        seed_cycle(
            simulator,
            robots,
        )

        selected = (
            self.detector.select_robot_to_reroute(
                robots
            )
        )

        self.assertIsNotNone(
            selected
        )

        # Robot 2 has the lowest priority.
        self.assertEqual(
            selected.robot_id,
            2,
        )

    def test_resolve_releases_selected_reservation(self):
        simulator, robots = build_deadlock()

        paths = seed_cycle(
            simulator,
            robots,
        )

        table = simulator.reservation_table

        # Robot 2 owns this reservation.
        self.assertEqual(
            table.get_owner(
                paths[1][-1],
                1,
            ),
            2,
        )

        result = self.detector.resolve_deadlock(
            robots
        )

        self.assertTrue(
            result["detected"]
        )

        self.assertEqual(
            result["rerouted_robot_id"],
            2,
        )

        # Robot 2's reservation was released.
        self.assertNotEqual(
            table.get_owner(
                paths[1][-1],
                1,
            ),
            2,
        )

    def test_scenario_completes_without_collisions(self):
        simulator, robots = build_deadlock()

        summary = simulator.run(
            steps=500
        )

        self.assertEqual(
            summary["collisions"],
            0,
        )

        self.assertEqual(
            summary["tasks_completed"],
            3,
        )


if __name__ == "__main__":
    unittest.main()