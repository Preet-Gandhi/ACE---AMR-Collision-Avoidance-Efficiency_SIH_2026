import math
import unittest

from planning.orca import ORCAAgent, ORCASolver


class OrcaTests(unittest.TestCase):
    def setUp(self):
        self.solver = ORCASolver(neighbor_distance=3.0, time_horizon=2.0, timestep=0.1)

    def test_preferred_velocity_is_kept_without_neighbors(self):
        agent = ORCAAgent((0.0, 0.0), preferred_velocity=(1.0, 0.0), max_speed=1.0)
        result = self.solver.compute_velocity(agent, [])
        self.assertTrue(result.feasible)
        self.assertAlmostEqual(result.velocity[0], 1.0)
        self.assertAlmostEqual(result.velocity[1], 0.0)
        self.assertEqual(result.constraints, 0)

    def test_nearby_head_on_robot_changes_velocity(self):
        agent = ORCAAgent((0.0, 0.0), velocity=(1.0, 0.0), preferred_velocity=(1.0, 0.0), max_speed=1.0)
        other = ORCAAgent((1.0, 0.0), velocity=(-1.0, 0.0), max_speed=1.0)
        result = self.solver.compute_velocity(agent, [other])
        self.assertGreater(result.constraints, 0)
        self.assertTrue(result.feasible)
        self.assertLess(result.velocity[0], 1.0)

    def test_distant_robot_is_ignored(self):
        agent = ORCAAgent((0.0, 0.0), preferred_velocity=(1.0, 0.0), max_speed=1.0)
        other = ORCAAgent((10.0, 0.0), velocity=(-1.0, 0.0), max_speed=1.0)
        result = self.solver.compute_velocity(agent, [other])
        self.assertEqual(result.constraints, 0)
        self.assertEqual(result.velocity, (1.0, 0.0))

    def test_velocity_is_capped(self):
        agent = ORCAAgent((0.0, 0.0), preferred_velocity=(10.0, 0.0), max_speed=1.0)
        result = self.solver.compute_velocity(agent, [])
        self.assertLessEqual(math.hypot(*result.velocity), 1.0 + 1e-7)

    def test_overlapping_agents_fall_back_safely(self):
        agent = ORCAAgent((0.0, 0.0), preferred_velocity=(1.0, 0.0), max_speed=1.0)
        other = ORCAAgent((0.0, 0.0), max_speed=1.0)
        result = self.solver.compute_velocity(agent, [other])
        self.assertEqual(result.velocity, (0.0, 0.0))
        self.assertTrue(result.used_fallback or result.velocity == (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
