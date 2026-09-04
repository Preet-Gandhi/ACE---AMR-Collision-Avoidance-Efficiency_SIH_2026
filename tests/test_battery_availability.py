import unittest

from auction.auction import Auction
from auction.bid import Bid
from auction.task import Task
from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.warehouse import Warehouse
from simulation.metrics import Metrics
from simulation.simulator import Simulator


class BatteryAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.warehouse = Warehouse((6, 6))
        self.network = Network()
        self.reservations = ReservationTable()
        self.planner = AStarPlanner(self.warehouse)
        self.robot = Robot(
            0, (0, 0), self.warehouse, self.planner, self.network,
            self.reservations, battery=2, battery_consumption_per_move=1,
        )
        self.other = Robot(
            1, (5, 5), self.warehouse, self.planner, self.network,
            self.reservations, battery=20,
        )
        self.auction = Auction(self.network, [self.robot, self.other])

    def test_battery_drains_and_robot_goes_offline_at_zero(self):
        self.robot.state.set_path([(1, 0), (2, 0)])
        self.assertTrue(self.robot.move())
        self.assertEqual(self.robot.state.battery, 1)
        self.assertTrue(self.robot.is_online())
        self.assertTrue(self.robot.move())
        self.assertEqual(self.robot.state.battery, 0)
        self.assertFalse(self.robot.is_online())
        self.assertEqual(self.robot.state.status, "DISCHARGED")
        self.assertEqual(self.robot.state.availability_state, "DISCHARGED")

    def test_offline_robot_cannot_bid_or_win(self):
        self.robot.state.battery = 0
        self.robot.go_offline()
        task = Task(1, (0, 1), (1, 1))
        self.assertFalse(self.robot.can_bid(task))
        winner = self.auction.select_winner([
            Bid(self.robot.robot_id, task.task_id, 0),
            Bid(self.other.robot_id, task.task_id, 10),
        ])
        self.assertEqual(winner.robot_id, self.other.robot_id)

    def test_offline_transition_releases_reservations_and_requeues_task(self):
        task = Task(1, (0, 1), (2, 0))
        task.assign(self.robot.robot_id)
        self.robot.accept_task(task)
        self.reservations.reserve_path(self.robot.robot_id, [(0, 0), (1, 0)])
        self.robot.state.battery = 0
        self.robot.go_offline()
        self.assertEqual(self.reservations.get_robot_reservations(self.robot.robot_id), [])
        self.assertEqual(task.assigned_robot_id, self.other.robot_id)
        self.assertEqual(task.status.value, "IN_PROGRESS")

    def test_completed_task_is_not_requeued_on_final_move(self):
        self.robot.state.battery = 1
        task = Task(1, (0, 0), (1, 0))
        task.assign(self.robot.robot_id)
        self.robot.accept_task(task)
        self.robot.state.set_path([(1, 0)])
        self.robot.move()
        self.assertFalse(self.robot.is_online())
        self.assertTrue(self.robot.is_task_complete())
        self.robot.complete_task()
        self.assertFalse(task.is_available())
        self.assertEqual(task.status.value, "COMPLETED")

    def test_state_broadcast_contains_battery_and_online_state(self):
        self.robot.broadcast_state()
        message = self.network.receive(self.other.robot_id)[0]
        self.assertEqual(message.payload["battery"], 2)
        self.assertTrue(message.payload["online"])

    def test_discharge_state_is_visible_in_dashboard_text(self):
        from dashboard.components import ComponentFormatter
        from dashboard.snapshot import SnapshotNormalizer
        from dashboard.svg_view import SvgWarehouseRenderer

        self.robot.state.battery = 0
        self.robot.go_offline()
        snapshot = SnapshotNormalizer.normalize({"robots": [self.robot]})
        output = ComponentFormatter.render_fleet_status(snapshot.robots)
        self.assertIn("DISCHARGED", output)
        svg = SvgWarehouseRenderer.render_svg(snapshot)
        self.assertIn("#dc2626", svg)

    def test_offline_robot_cell_blocks_active_robot_movement(self):
        self.robot.state.battery = 0
        self.robot.go_offline()
        simulator = Simulator(
            self.warehouse, [self.robot, self.other], self.network,
            self.reservations, Metrics(), self.auction, dt=0.1,
        )
        self.other.state.set_path([(0, 0)])
        simulator.step()
        self.assertEqual(self.other.state.position, (5, 5))

    def test_low_battery_robot_reaches_station_and_recharges(self):
        charging_robot = Robot(
            9, (1, 0), self.warehouse, self.planner, self.network,
            self.reservations, battery=1, charging_station=(0, 0),
            charging_rate_per_step=1,
        )
        charging_auction = Auction(self.network, [charging_robot])
        simulator = Simulator(
            self.warehouse, [charging_robot], self.network,
            self.reservations, Metrics(), charging_auction, dt=0.1,
        )
        simulator.step()
        self.assertEqual(charging_robot.state.availability_state, "GOING_TO_CHARGER")
        simulator.step()
        self.assertEqual(charging_robot.state.position, (0, 0))
        self.assertEqual(charging_robot.state.availability_state, "CHARGING")
        simulator.step()
        self.assertTrue(charging_robot.is_online())
        self.assertEqual(charging_robot.state.battery, 1)


if __name__ == "__main__":
    unittest.main()
