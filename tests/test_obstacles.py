import unittest

from auction.auction import Auction
from auction.task import Task
from communication.message import Message, MessageType
from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.warehouse import Warehouse


class ObstacleTests(unittest.TestCase):
    def setUp(self):
        self.warehouse = Warehouse((5, 3))
        self.network = Network()
        self.reservations = ReservationTable()
        self.robot = Robot(0, (0, 1), self.warehouse, AStarPlanner(self.warehouse), self.network, self.reservations)
        self.task = Task(1, (0, 1), (4, 1)); self.warehouse.add_task(self.task)
        self.task.assign(0); self.robot.accept_task(self.task); self.robot.set_time(0); self.robot.plan_path()

    def test_obstacle_invalidates_path_and_replans(self):
        blocked = self.robot.state.path[1]
        self.warehouse.add_obstacle(blocked)
        self.assertFalse(self.robot.is_path_valid())
        self.assertTrue(self.robot.handle_obstacle(blocked))
        self.assertTrue(self.robot.is_path_valid())
        self.assertNotIn(blocked, self.robot.state.path)

    def test_obstacle_detection_is_broadcast(self):
        peer = Robot(1, (4, 2), self.warehouse, AStarPlanner(self.warehouse), self.network, self.reservations)
        self.robot.handle_obstacle(self.robot.state.path[1])
        messages = self.network.receive(peer.robot_id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message_type, MessageType.OBSTACLE_DETECTED)

    def test_unreachable_task_is_failed_and_released(self):
        auction = Auction(self.network, [self.robot])
        self.robot.wait_threshold = 0.1
        for y in range(self.warehouse.height): self.warehouse.add_obstacle((1, y))
        self.robot.handle_obstacle((1, 1))
        self.robot.set_time(1); self.robot.update()
        self.assertIsNone(self.robot.state.current_task_id)
        self.assertTrue(self.task.is_available())


if __name__ == "__main__": unittest.main()
