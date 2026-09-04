import random

from auction.auction import Auction
from auction.task import Task
from communication.network import Network
from config import Config
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.metrics import Metrics
from simulation.simulator import Simulator
from simulation.warehouse import Warehouse


class BenchmarkRobot(Robot):
    """Keep completed robots physically safe as stationary obstacles."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._idle_hold_until = -1

    def set_time(self, timestep):
        super().set_time(timestep)
        if self.state.current_task_id is None and timestep >= self._idle_hold_until - 100:
            self.reservation_table.release(self.robot_id)
            hold_length = 1_000
            for offset in range(hold_length):
                self.reservation_table.reserve(self.robot_id, self.state.position, timestep + offset)
            self._idle_hold_until = timestep + hold_length


def create_tasks(seed, task_count, width=30, height=20):
    rng = random.Random(seed)
    tasks = []
    for task_id in range(task_count):
        pickup = (rng.randrange(width), rng.randrange(height))
        dropoff = (rng.randrange(width), rng.randrange(height))
        while dropoff == pickup: dropoff = (rng.randrange(width), rng.randrange(height))
        tasks.append(Task(task_id, pickup, dropoff, priority=rng.randrange(4), created_time=0.0))
    return tasks


def build_benchmark(seed, robot_count=3, task_count=20, mode="distributed"):
    config = Config()
    warehouse = Warehouse((config.grid_width, config.grid_height))
    network, reservations, metrics = Network(), ReservationTable(), Metrics()
    planner = AStarPlanner(warehouse)
    starts = [(i % config.grid_width, i // config.grid_width) for i in range(robot_count)]
    robot_type = BenchmarkRobot if mode == "distributed" else Robot
    robots = [robot_type(i, start, warehouse, planner, network, reservations, battery=10_000.0, robot_speed=config.robot_speed, congestion_penalty=config.congestion_penalty, priority_bonus=config.priority_bonus, invalid_bid_penalty=config.invalid_bid_penalty) for i, start in enumerate(starts)]
    auction = Auction(network, robots)
    tasks = create_tasks(seed, task_count, config.grid_width, config.grid_height)
    for task in tasks: warehouse.add_task(task); auction.run_auction(task, verbose=False)
    simulator = Simulator(warehouse, robots, network, reservations, metrics, auction, config.simulation_dt)
    return simulator, robots, tasks


def run_mode(mode, seed, robot_count=3, task_count=20, max_steps=None):
    simulator, robots, tasks = build_benchmark(seed, robot_count, task_count, mode)
    max_steps = max_steps or max(2_000, task_count * 1_000)
    if mode == "baseline": run_sequential_baseline(simulator, robots, max_steps)
    elif mode == "distributed": simulator.run(max_steps)
    else: raise ValueError("mode must be 'baseline' or 'distributed'")
    waiting_time = sum(robot.waiting_time for robot in robots)
    return simulator.metrics.to_benchmark_result(mode, seed, robot_count, task_count, waiting_time=waiting_time)


def run_sequential_baseline(simulator, robots, max_steps):
    """Run the reference policy one robot at a time without changing Simulator."""
    simulator.metrics.start_simulation(simulator.time)
    steps = 0
    for robot in robots:
        while robot.state.current_task_id is not None and steps < max_steps:
            timestep = round(simulator.time / simulator.dt)
            robot.set_time(timestep)
            simulator.reservation_table.release_expired(timestep)
            robot.update()
            if robot.state.get_next_position() is None: robot.plan_path()
            if robot.move(): simulator.metrics.record_movement(robot, 1.0)
            if robot.is_task_complete():
                task = robot.tasks[robot.state.current_task_id]
                robot.complete_task()
                simulator.metrics.record_task_completed(task, robot)
            simulator.time += simulator.dt
            steps += 1
    simulator.metrics.end_simulation(simulator.time)


def run_comparison(seed, robot_count=3, task_count=20, max_steps=None):
    baseline = run_mode("baseline", seed, robot_count, task_count, max_steps)
    distributed = run_mode("distributed", seed, robot_count, task_count, max_steps)
    improvement = Metrics.calculate_improvement(baseline["completion_time"], distributed["completion_time"])
    distributed["improvement"] = improvement
    baseline["improvement"] = None
    return {"baseline": baseline, "distributed": distributed}


def run_matrix(seeds=(42, 43, 44, 45, 46), task_counts=(20, 50, 100), robot_count=3, max_steps=None):
    return [run_comparison(seed, robot_count, task_count, max_steps) for task_count in task_counts for seed in seeds]
