import unittest

from planning.deadlock import DeadlockDetector
from scenarios.deadlock import build


class DeadlockScenarioTests(unittest.TestCase):
    def test_cycle_is_detected_and_one_robot_is_rerouted(self):
        simulator, robots, _ = build()
        detector = DeadlockDetector()
        result = detector.detect_deadlocks(robots)
        self.assertTrue(result["detected"])
        self.assertEqual(set(result["robots"]), {0, 1, 2})
        resolved = detector.resolve_deadlock(robots)
        self.assertTrue(resolved["detected"])
        self.assertIn(resolved["rerouted_robot_id"], {0, 1, 2})
        self.assertEqual(simulator.reservation_table.get_robot_reservations(resolved["rerouted_robot_id"]), [])


if __name__ == "__main__": unittest.main()
