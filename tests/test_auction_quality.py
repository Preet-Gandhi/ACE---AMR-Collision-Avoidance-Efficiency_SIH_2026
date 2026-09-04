import io
import unittest
from contextlib import redirect_stdout

from auction.auction import Auction
from auction.bid import Bid
from auction.task import Task
from communication.network import Network
from planning.astar import AStarPlanner
from planning.reservation import ReservationTable
from robots.robot import Robot
from simulation.warehouse import Warehouse


class AuctionQualityTests(unittest.TestCase):
    def setUp(self):
        self.warehouse = Warehouse((10, 10))
        self.network = Network()
        self.reservations = ReservationTable()
        self.planner = AStarPlanner(self.warehouse)
        self.robots = [Robot(i, (i, 0), self.warehouse, self.planner, self.network, self.reservations) for i in range(3)]
        self.auction = Auction(self.network, self.robots)

    def test_bid_breakdown_and_priority(self):
        task = Task(1, (0, 1), (2, 2), priority=2)
        bid = self.robots[0].calculate_bid(task)
        self.assertAlmostEqual(bid.total_cost, bid.travel_cost + bid.time_cost + bid.battery_cost + bid.congestion_cost - bid.priority_bonus)
        high_priority = self.robots[0].calculate_bid(Task(2, (0, 1), (2, 2), priority=4))
        self.assertLess(high_priority.total_cost, bid.total_cost)

    def test_longer_path_and_battery(self):
        near = self.robots[0].calculate_bid(Task(1, (0, 1), (1, 1)))
        far = self.robots[0].calculate_bid(Task(2, (0, 1), (8, 8)))
        self.assertLess(near.total_cost, far.total_cost)
        low_battery = Robot(9, (0, 0), self.warehouse, self.planner, self.network, self.reservations, battery=1)
        self.assertFalse(low_battery.calculate_bid(Task(3, (0, 1), (8, 8))).valid)

    def test_five_tasks_have_unique_winners(self):
        results = []
        for i in range(5):
            task = Task(i, (i, 1), (9 - i, 9), priority=i % 3)
            self.warehouse.add_task(task)
            results.append(self.auction.run_auction(task, verbose=False))
        winners = [result.winner.robot_id for result in results if result.winner]
        assigned = [task.assigned_robot_id for task in self.warehouse.tasks.values()]
        self.assertEqual(len(assigned), 5)
        self.assertEqual(len(winners), 5)
        self.assertTrue(all(task.assigned_robot_id is not None for task in self.warehouse.tasks.values()))
        self.assertTrue(all(len(robot.task_queue) + int(robot.state.current_task_id is not None) >= 1 for robot in self.robots))

    def test_completed_task_is_not_reauctioned(self):
        task = Task(1, (0, 1), (1, 1)); self.warehouse.add_task(task)
        first = self.auction.run_auction(task, verbose=False)
        task.complete()
        second = self.auction.run_auction(task, verbose=False)
        self.assertIsNotNone(first.winner)
        self.assertIsNone(second.winner)
        self.assertEqual(self.warehouse.get_pending_tasks(), [])

    def test_tie_break_and_output(self):
        winner = self.auction.select_winner([Bid(2, 1, 4), Bid(0, 1, 4), Bid(1, 1, 4)])
        self.assertEqual(winner.robot_id, 0)
        task = Task(1, (0, 1), (1, 1)); self.warehouse.add_task(task)
        output = io.StringIO()
        with redirect_stdout(output): self.auction.run_auction(task)
        self.assertIn("TASK 2", output.getvalue())
        self.assertIn("WINNER: R1", output.getvalue())

    def test_queued_tasks_start_sequentially(self):
        first, second = Task(1, (0, 1), (1, 1)), Task(2, (1, 1), (2, 2))
        first.assign(0); self.robots[0].accept_task(first)
        second.assign(0); self.robots[0].accept_task(second)
        self.assertEqual(self.robots[0].state.current_task_id, 1)
        self.assertEqual([task.task_id for task in self.robots[0].task_queue], [2])
        self.robots[0].complete_task()
        self.assertEqual(self.robots[0].state.current_task_id, 2)


if __name__ == "__main__": unittest.main()
