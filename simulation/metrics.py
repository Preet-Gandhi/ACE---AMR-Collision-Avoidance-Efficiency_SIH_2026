from dataclasses import asdict, dataclass


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


class Metrics:
    def __init__(self):
        self.collisions = 0; self.tasks_completed = 0; self.total_distance = 0.0; self.waiting_time = 0.0; self.replanning_count = 0; self.deadlocks = 0; self.start_time = None; self.end_time = None; self.task_times = []
    def start_simulation(self, now=0.0): self.start_time = now
    def end_simulation(self, now=0.0): self.end_time = now
    def record_collision(self, robot_a, robot_b): self.collisions += 1
    def record_task_completed(self, task, robot): self.tasks_completed += 1; self.task_times.append(task.created_time)
    def record_movement(self, robot, distance): self.total_distance += distance
    def record_wait(self, robot, duration): self.waiting_time += duration
    def record_replan(self, robot): self.replanning_count += 1
    def record_deadlock(self, robots): self.deadlocks += 1
    def get_completion_time(self): return (self.end_time - self.start_time) if self.start_time is not None and self.end_time is not None else 0.0
    def get_average_task_time(self): return sum(self.task_times) / len(self.task_times) if self.task_times else 0.0
    def get_collision_count(self): return self.collisions
    def get_summary(self):
        completion_time = self.get_completion_time()
        return {"collisions": self.collisions, "tasks_completed": self.tasks_completed, "total_distance": self.total_distance, "waiting_time": self.waiting_time, "replanning_count": self.replanning_count, "deadlocks": self.deadlocks, "completion_time": completion_time, "throughput": self.tasks_completed / completion_time if completion_time else 0.0}
    def to_benchmark_result(self, mode, seed, robot_count, task_count, improvement=None, waiting_time=None, replans=None):
        summary = self.get_summary()
        return BenchmarkResult(mode, seed, robot_count, task_count, summary["completion_time"], summary["throughput"], summary["collisions"], summary["deadlocks"], summary["waiting_time"] if waiting_time is None else waiting_time, summary["total_distance"], summary["replanning_count"] if replans is None else replans, improvement).to_dict()
    @staticmethod
    def calculate_improvement(baseline_time, proposed_time): return ((baseline_time - proposed_time) / baseline_time * 100) if baseline_time else 0.0
