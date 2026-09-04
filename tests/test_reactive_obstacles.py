import unittest

from auction.task import Task
from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.warehouse import Warehouse


class ReactiveObstacleTests(unittest.TestCase):
    def build_robot(self, horizon=20, sensor_radius=2, safety_radius=0):
        warehouse = Warehouse((8, 3))
        network = Network()
        reservations = ReservationTable()
        robot = Robot(
            0,
            (0, 1),
            warehouse,
            AStarPlanner(warehouse),
            network,
            reservations,
            reservation_horizon=horizon,
            obstacle_sensor_radius=sensor_radius,
            obstacle_safety_radius=safety_radius,
        )
        task = Task(1, (0, 1), (7, 1))
        warehouse.add_task(task)
        task.assign(robot.robot_id)
        robot.accept_task(task)
        robot.set_time(0)
        robot.plan_path()
        return warehouse, robot, reservations

    def test_local_obstacle_detection_replans_before_entry(self):
        warehouse, robot, _ = self.build_robot(sensor_radius=2)
        warehouse.add_obstacle((1, 1))

        robot.update()

        self.assertIn((1, 1), robot.known_obstacles)
        self.assertNotIn((1, 1), robot.state.path)
        self.assertNotEqual(robot.state.get_next_position(), (1, 1))

    def test_reservations_use_forward_rolling_horizon(self):
        _, robot, reservations = self.build_robot(horizon=2, sensor_radius=0)

        self.assertEqual(reservations.get_owner((0, 1), 0), robot.robot_id)
        self.assertEqual(reservations.get_owner((2, 1), 2), robot.robot_id)
        self.assertIsNone(reservations.get_owner((3, 1), 3))


if __name__ == "__main__":
    unittest.main()
