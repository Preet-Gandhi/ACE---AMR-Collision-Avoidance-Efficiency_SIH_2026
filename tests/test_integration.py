import unittest

from auction.auction import Auction
from auction.task import Task
from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.metrics import Metrics
from simulation.simulator import Simulator
from simulation.warehouse import Warehouse


class IntegrationTests(unittest.TestCase):
    def test_three_robot_mvp(self):
        warehouse = Warehouse((8, 8)); network = Network(); reservations = ReservationTable(); metrics = Metrics()
        planner = AStarPlanner(warehouse)
        robots = [Robot(i, (i, 0), warehouse, planner, network, reservations) for i in range(3)]
        auction = Auction(network, robots)
        for i in range(3):
            task = Task(i, (i, 1), (7 - i, 7)); warehouse.add_task(task); auction.run_auction(task)
        simulator = Simulator(warehouse, robots, network, reservations, metrics, auction)
        summary = simulator.run(200)
        self.assertEqual(summary["collisions"], 0)
        self.assertEqual(summary["tasks_completed"], 3)


if __name__ == "__main__": unittest.main()
