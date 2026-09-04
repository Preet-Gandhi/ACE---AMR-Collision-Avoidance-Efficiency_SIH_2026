import unittest

from auction.task import Task, TaskStatus
from planning.astar import AStarPlanner
from planning.collision import CollisionDetector
from planning.reservation import ReservationTable
from simulation.warehouse import Warehouse


class CoreTests(unittest.TestCase):
    def test_warehouse_and_astar(self):
        warehouse = Warehouse((5, 5)); warehouse.add_obstacle((2, 2))
        path = AStarPlanner(warehouse).find_path((0, 0), (4, 4))
        self.assertEqual(path[0], (0, 0)); self.assertEqual(path[-1], (4, 4)); self.assertNotIn((2, 2), path)

    def test_unreachable_goal(self):
        warehouse = Warehouse([[0, 1, 0], [0, 1, 0], [0, 1, 0]])
        self.assertEqual(AStarPlanner(warehouse).find_path((0, 0), (2, 0)), [])

    def test_task_lifecycle(self):
        task = Task(1, (0, 0), (1, 1)); task.assign(3); task.start(); task.complete()
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_reservation_conflict(self):
        table = ReservationTable(); self.assertTrue(table.reserve_path(1, [(0, 0), (1, 0)]))
        self.assertFalse(table.reserve_path(2, [(0, 0), (1, 0)]))

    def test_edge_conflict(self):
        detector = CollisionDetector()
        self.assertTrue(detector.detect_edge_conflict([(0, 0), (1, 0)], [(1, 0), (0, 0)]))


if __name__ == "__main__": unittest.main()
