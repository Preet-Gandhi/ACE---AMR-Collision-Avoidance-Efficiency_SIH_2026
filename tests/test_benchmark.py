import unittest

from scenarios.benchmark import create_tasks, run_comparison, run_mode
from simulation.metrics import Metrics


class BenchmarkTests(unittest.TestCase):
    def test_task_generation_is_reproducible(self):
        self.assertEqual(create_tasks(42, 20), create_tasks(42, 20))
        self.assertNotEqual(create_tasks(42, 20), create_tasks(43, 20))

    def test_result_schema(self):
        result = run_mode("distributed", 42, robot_count=3, task_count=5, max_steps=500)
        self.assertEqual(set(result), {"mode", "seed", "robot_count", "task_count", "completion_time", "throughput", "collisions", "deadlocks", "waiting_time", "total_distance", "replans", "improvement"})
        self.assertEqual(result["mode"], "distributed")
        self.assertIsNone(result["improvement"])

    def test_comparison_and_improvement(self):
        comparison = run_comparison(42, robot_count=3, task_count=5, max_steps=500)
        baseline, distributed = comparison["baseline"], comparison["distributed"]
        expected = Metrics.calculate_improvement(baseline["completion_time"], distributed["completion_time"])
        self.assertEqual(distributed["improvement"], expected)
        self.assertIsNone(baseline["improvement"])

    def test_same_seed_same_result(self):
        self.assertEqual(run_mode("distributed", 42, 3, 5, 500), run_mode("distributed", 42, 3, 5, 500))


if __name__ == "__main__": unittest.main()
