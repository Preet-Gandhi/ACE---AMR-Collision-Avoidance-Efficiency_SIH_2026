import csv
import json
import tempfile
import unittest
from pathlib import Path

from benchmark import build_payload, write_results
from benchmark_report import format_report
from scenarios.benchmark import create_tasks, run_comparison, run_mode
from simulation.metrics import Metrics, aggregate_comparisons, benchmark_status


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

    def test_aggregation_mean_median_and_status(self):
        def row(mode, seed, time, improvement=None, collisions=0):
            return {"mode": mode, "seed": seed, "robot_count": 3, "task_count": 20, "completion_time": time, "throughput": 1.0, "collisions": collisions, "deadlocks": 0, "waiting_time": 2.0, "total_distance": 10.0, "replans": 1, "improvement": improvement}
        comparisons = [{"baseline": row("baseline", 1, 100), "distributed": row("distributed", 1, 80, 20)}, {"baseline": row("baseline", 2, 200), "distributed": row("distributed", 2, 150, 25)}]
        aggregate = aggregate_comparisons(comparisons)[0]
        self.assertEqual(aggregate["baseline_mean_time"], 150)
        self.assertEqual(aggregate["baseline_median_time"], 150)
        self.assertEqual(aggregate["mean_improvement"], 22.5)
        self.assertEqual(aggregate["status"], "PASS")
        self.assertEqual(benchmark_status(1, 50), "FAIL")
        self.assertEqual(benchmark_status(0, 19.9), "FAIL")

    def test_json_csv_and_report(self):
        comparisons = [run_comparison(42, 3, 5, 500)]
        payload = build_payload(comparisons, [42], [5], 3)
        with tempfile.TemporaryDirectory() as directory:
            json_path, csv_path = Path(directory) / "results.json", Path(directory) / "results.csv"
            write_results(payload, json_path, csv_path)
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("runs", saved); self.assertIn("aggregates", saved)
            with csv_path.open(newline="", encoding="utf-8") as output:
                rows = list(csv.DictReader(output))
            self.assertEqual(rows[0]["task_count"], "5")
            self.assertIn("AMR BENCHMARK REPORT", format_report(saved))


if __name__ == "__main__": unittest.main()
