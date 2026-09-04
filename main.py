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
    robots = [Robot(i, (i, 0), warehouse, planner, network, reservations, config.initial_battery) for i in range(config.num_robots)]
    auction = Auction(network, robots)
    for i in range(config.num_robots): warehouse.add_task(Task(i, (i, 1), (config.grid_width - i - 1, config.grid_height - 1), priority=i))
    for task in warehouse.get_pending_tasks(): auction.run_auction(task)
    return Simulator(warehouse, robots, network, reservations, metrics, auction, config.simulation_dt), robots


def main():
    simulator, _ = build_simulation()
    print(simulator.run())


if __name__ == "__main__": main()
