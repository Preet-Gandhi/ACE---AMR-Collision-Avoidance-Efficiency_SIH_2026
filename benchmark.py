import argparse
import json

from scenarios.benchmark import run_matrix


def main():
    parser = argparse.ArgumentParser(description="Run baseline vs distributed AMR benchmarks")
    parser.add_argument("--tasks", nargs="+", type=int, default=[20, 50, 100])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--robots", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(run_matrix(tuple(args.seeds), tuple(args.tasks), args.robots, args.max_steps), indent=2))


if __name__ == "__main__": main()
