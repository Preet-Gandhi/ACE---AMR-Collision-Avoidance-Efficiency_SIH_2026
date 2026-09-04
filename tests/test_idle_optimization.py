import unittest

from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.warehouse import Warehouse


class IdleOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.warehouse = Warehouse((5, 5))
        self.network = Network()
        self.reservations = ReservationTable()
        self.planner = AStarPlanner(self.warehouse)

    def test_offline_robot_not_in_connected_peers(self):
        online = Robot(1, (0, 0), self.warehouse, self.planner, self.network, self.reservations)
        offline = Robot(2, (1, 0), self.warehouse, self.planner, self.network, self.reservations)

        offline.state.online = False
        offline.state.availability_state = "OFFLINE"

        self.assertNotIn(offline.robot_id, self.network.get_connected_robots(online.robot_id))

    def test_robot_replans_after_sustained_block(self):
        robot = Robot(1, (0, 0), self.warehouse, self.planner, self.network, self.reservations)
        robot.current_time = 10
        robot.last_replan_time = 0
        robot.waiting_time = robot.wait_threshold
        robot.blockage_waiting = robot.wait_threshold

        self.assertTrue(robot._should_replan())

    def test_robot_does_not_replan_inside_cooldown(self):
        robot = Robot(1, (0, 0), self.warehouse, self.planner, self.network, self.reservations)
        robot.current_time = 10
        robot.last_replan_time = 9
        robot.replan_cooldown = 2.0
        robot.waiting_time = robot.wait_threshold
        robot.blockage_waiting = robot.wait_threshold

        self.assertFalse(robot._should_replan())


if __name__ == "__main__":
    unittest.main()
