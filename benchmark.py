import argparse
import csv
import json
from pathlib import Path

from scenarios.benchmark import run_matrix
from simulation.metrics import RESULT_FIELDS, aggregate_comparisons


def build_payload(comparisons, seeds, task_counts, robot_count):
    return {"robot_count": robot_count, "seeds": list(seeds), "task_counts": list(task_counts), "runs": comparisons, "aggregates": aggregate_comparisons(comparisons)}


def write_results(payload, json_path="benchmark_results.json", csv_path="benchmark_results.csv"):
    Path(json_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fields = list(payload["aggregates"][0].keys()) if payload["aggregates"] else ["robot_count", "task_count", "seed_count"]
    with Path(csv_path).open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader(); writer.writerows(payload["aggregates"])


def run_and_export(seeds, task_counts, robot_count, max_steps=None, json_path="benchmark_results.json", csv_path="benchmark_results.csv"):
    comparisons = run_matrix(tuple(seeds), tuple(task_counts), robot_count, max_steps)
    payload = build_payload(comparisons, seeds, task_counts, robot_count)
    write_results(payload, json_path, csv_path)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Run baseline vs distributed AMR benchmarks")
    parser.add_argument("--tasks", nargs="+", type=int, default=[20, 50, 100])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--robots", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--json", default="benchmark_results.json", help="JSON output path")
    parser.add_argument("--csv", dest="csv_path", default="benchmark_results.csv", help="CSV output path")
    args = parser.parse_args()
    payload = run_and_export(args.seeds, args.tasks, args.robots, args.max_steps, args.json, args.csv_path)
    print(json.dumps(payload["aggregates"], indent=2))


if __name__ == "__main__": main()
