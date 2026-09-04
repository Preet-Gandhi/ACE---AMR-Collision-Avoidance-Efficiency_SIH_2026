from dataclasses import asdict, dataclass
from statistics import mean, median


@dataclass(frozen=True)
class BenchmarkResult:
    mode: str
    seed: int
    robot_count: int
    task_count: int
    completion_time: float
    throughput: float
    collisions: int
    deadlocks: int
    waiting_time: float
    total_distance: float
    replans: int
    improvement: float | None

    def to_dict(self): return asdict(self)


RESULT_FIELDS = ("mode", "seed", "robot_count", "task_count", "completion_time", "throughput", "collisions", "deadlocks", "waiting_time", "total_distance", "replans", "improvement")


def benchmark_status(collisions, improvement, minimum_improvement=20.0):
    return "PASS" if collisions == 0 and improvement >= minimum_improvement else "FAIL"


def aggregate_comparisons(comparisons):
    groups = {}
    for comparison in comparisons:
        distributed = comparison["distributed"]
        key = (distributed["robot_count"], distributed["task_count"])
        groups.setdefault(key, []).append(comparison)
    aggregates = []
    for (robot_count, task_count), rows in sorted(groups.items()):
        baseline_times = [row["baseline"]["completion_time"] for row in rows]
        distributed_rows = [row["distributed"] for row in rows]
        improvements = [row["distributed"]["improvement"] for row in rows]
        total_collisions = sum(row["distributed"]["collisions"] for row in rows)
        total_deadlocks = sum(row["distributed"]["deadlocks"] for row in rows)
        mean_improvement = mean(improvements) if improvements else 0.0
        aggregates.append({
            "robot_count": robot_count,
            "task_count": task_count,
            "seed_count": len(rows),
            "baseline_mean_time": mean(baseline_times),
            "baseline_median_time": median(baseline_times),
            "distributed_mean_time": mean(row["completion_time"] for row in distributed_rows),
            "distributed_median_time": median(row["completion_time"] for row in distributed_rows),
            "mean_throughput": mean(row["throughput"] for row in distributed_rows),
            "mean_waiting_time": mean(row["waiting_time"] for row in distributed_rows),
            "mean_total_distance": mean(row["total_distance"] for row in distributed_rows),
            "mean_replans": mean(row["replans"] for row in distributed_rows),
            "total_collisions": total_collisions,
            "total_deadlocks": total_deadlocks,
            "mean_improvement": mean_improvement,
            "status": benchmark_status(total_collisions, mean_improvement),
        })
    return aggregates


class Metrics:
    def __init__(self):
        self.collisions = 0; self.tasks_completed = 0; self.total_distance = 0.0; self.waiting_time = 0.0; self.replanning_count = 0; self.deadlocks = 0; self.start_time = None; self.end_time = None; self.task_times = []
        self.orca_constraints = 0; self.orca_stops = 0; self.orca_moves = 0; self.orca_velocity_deviation = 0.0; self.orca_velocity_samples = 0; self.orca_fallbacks = 0
    def start_simulation(self, now=0.0): self.start_time = now
    def end_simulation(self, now=0.0): self.end_time = now
    def record_collision(self, robot_a, robot_b): self.collisions += 1
    def record_task_completed(self, task, robot): self.tasks_completed += 1; self.task_times.append(task.created_time)
    def record_movement(self, robot, distance): self.total_distance += distance
    def record_wait(self, robot, duration): self.waiting_time += duration
    def record_replan(self, robot): self.replanning_count += 1
    def record_deadlock(self, robots): self.deadlocks += 1
    def record_orca(self, result, preferred_velocity, moved=True):
        self.orca_constraints += result.constraints
        if not moved:
            self.orca_stops += 1
        elif moved:
            self.orca_moves += 1
        self.orca_velocity_deviation += ((result.velocity[0] - preferred_velocity[0]) ** 2 + (result.velocity[1] - preferred_velocity[1]) ** 2) ** 0.5
        self.orca_velocity_samples += 1
        if result.used_fallback: self.orca_fallbacks += 1
    def get_completion_time(self): return (self.end_time - self.start_time) if self.start_time is not None and self.end_time is not None else 0.0
    def get_average_task_time(self): return sum(self.task_times) / len(self.task_times) if self.task_times else 0.0
    def get_collision_count(self): return self.collisions
    def get_summary(self):
        completion_time = self.get_completion_time()
        return {"collisions": self.collisions, "tasks_completed": self.tasks_completed, "total_distance": self.total_distance, "waiting_time": self.waiting_time, "replanning_count": self.replanning_count, "deadlocks": self.deadlocks, "completion_time": completion_time, "throughput": self.tasks_completed / completion_time if completion_time else 0.0, "orca_constraints": self.orca_constraints, "orca_stops": self.orca_stops, "orca_moves": self.orca_moves, "orca_velocity_deviation": self.orca_velocity_deviation / self.orca_velocity_samples if self.orca_velocity_samples else 0.0, "orca_fallbacks": self.orca_fallbacks}
    def to_benchmark_result(self, mode, seed, robot_count, task_count, improvement=None, waiting_time=None, replans=None):
        summary = self.get_summary()
        return BenchmarkResult(mode, seed, robot_count, task_count, summary["completion_time"], summary["throughput"], summary["collisions"], summary["deadlocks"], summary["waiting_time"] if waiting_time is None else waiting_time, summary["total_distance"], summary["replanning_count"] if replans is None else replans, improvement).to_dict()
    @staticmethod
    def calculate_improvement(baseline_time, proposed_time): return ((baseline_time - proposed_time) / baseline_time * 100) if baseline_time else 0.0
