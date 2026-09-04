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


def build_simulation(config=None):
    config = config or Config(); warehouse = Warehouse((config.grid_width, config.grid_height))
    network, reservations, metrics = Network(), ReservationTable(), Metrics()
    planner = AStarPlanner(warehouse)
    robots = [Robot(i, (i, 0), warehouse, planner, network, reservations, config.initial_battery, config.robot_speed, config.congestion_penalty, config.priority_bonus, config.invalid_bid_penalty) for i in range(config.num_robots)]
    auction = Auction(network, robots)
    tasks = [
        Task(0, (0, 1), (config.grid_width - 1, config.grid_height - 1), priority=1),
        Task(1, (1, 2), (config.grid_width - 2, config.grid_height - 2), priority=3),
        Task(2, (2, 3), (config.grid_width - 3, config.grid_height - 3), priority=2),
        Task(3, (3, 4), (config.grid_width - 4, config.grid_height - 4), priority=5),
        Task(4, (4, 5), (config.grid_width - 5, config.grid_height - 5), priority=0),
    ]
    for task in tasks: warehouse.add_task(task)
    for task in warehouse.get_pending_tasks(): auction.run_auction(task)
    return Simulator(warehouse, robots, network, reservations, metrics, auction, config.simulation_dt), robots


def main():
    simulator, _ = build_simulation()
    print(simulator.run())


if __name__ == "__main__": main()
