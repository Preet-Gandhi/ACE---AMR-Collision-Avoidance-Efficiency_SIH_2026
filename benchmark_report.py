import argparse
import json
from pathlib import Path


def load_payload(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def format_report(payload):
    lines = []
    for aggregate in payload.get("aggregates", []):
        lines.extend([
            "AMR BENCHMARK REPORT",
            f"Robots: {aggregate['robot_count']}",
            f"Tasks: {aggregate['task_count']}",
            f"Seeds: {aggregate['seed_count']}",
            "",
            f"Baseline mean time:      {aggregate['baseline_mean_time']:.2f} sec",
            f"Distributed mean time:   {aggregate['distributed_mean_time']:.2f} sec",
            f"Mean improvement:        {aggregate['mean_improvement']:.2f}%",
            f"Total collisions:        {aggregate['total_collisions']}",
            f"Total deadlocks:         {aggregate['total_deadlocks']}",
            f"Mean throughput:         {aggregate['mean_throughput']:.4f} tasks/sec",
            f"Mean waiting time:       {aggregate['mean_waiting_time']:.2f} sec",
            f"Mean travel distance:    {aggregate['mean_total_distance']:.2f}",
            f"Mean replans:            {aggregate['mean_replans']:.2f}",
            f"Status: {aggregate['status']}",
            "",
        ])
    return "\n".join(lines).rstrip()


def main():
    parser = argparse.ArgumentParser(description="Print an AMR benchmark presentation report")
    parser.add_argument("results", help="Path to benchmark_results.json")
    args = parser.parse_args()
    print(format_report(load_payload(args.results)))


if __name__ == "__main__": main()
