import unittest

from planning.collision import CollisionDetector
from planning.reservation import ReservationTable


class CollisionTests(unittest.TestCase):
    def setUp(self): self.detector = CollisionDetector()

    def test_vertex_conflict(self):
        self.assertTrue(self.detector.detect_vertex_conflict([(0, 0), (1, 0)], [(2, 0), (1, 0)]))

    def test_edge_conflict(self):
        self.assertTrue(self.detector.detect_edge_conflict([(0, 0), (1, 0)], [(1, 0), (0, 0)]))
        self.assertFalse(self.detector.detect_edge_conflict([(0, 0), (1, 0)], [(2, 0), (2, 1)]))

    def test_future_vertex_conflict(self):
        self.assertTrue(self.detector.detect_future_conflict([(0, 0), (1, 0), (2, 0)], [(3, 0), (1, 0), (4, 0)]))

    def test_shorter_path_holds_final_position(self):
        self.assertTrue(self.detector.detect_vertex_conflict([(0, 0), (1, 0)], [(2, 0), (1, 0), (1, 0)]))

    def test_reservation_rejects_vertex_and_edge_conflicts(self):
        table = ReservationTable()
        self.assertTrue(table.reserve_path(1, [(0, 0), (1, 0)]))
        self.assertFalse(table.can_reserve(2, [(1, 0), (0, 0)]))
        self.assertFalse(table.can_reserve(2, [(0, 0), (1, 0)]))


if __name__ == "__main__": unittest.main()
