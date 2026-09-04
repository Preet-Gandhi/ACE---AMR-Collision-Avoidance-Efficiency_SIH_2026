import unittest

from auction.auction import Auction
from auction.task import Task, TaskStatus
from communication.message import Message, MessageType
from communication.network import Network
from planning.reservation import ReservationTable


class ProtocolRegressionTests(unittest.TestCase):
    def test_stale_claim_from_previous_round_is_rejected(self):
        network = Network()
        auction = Auction(network, [])
        task = Task(1, (0, 0), (1, 0))

        auction.announce_task(task)
        first_id = auction.auction_ids[task.task_id]
        auction.announce_task(task)

        accepted = auction.receive_claim(Message(
            0,
            MessageType.AUCTION_CLAIM,
            0.0,
            {"task_id": task.task_id, "robot_id": 0, "auction_id": first_id, "round": 0},
        ))

        self.assertFalse(accepted)
        self.assertNotIn(task.task_id, auction.claims)
        self.assertEqual(task.status, TaskStatus.AUCTIONING)

    def test_reservation_lease_expiry_releases_vertices_and_edges(self):
        table = ReservationTable()
        self.assertTrue(table.reserve_path(1, [(0, 0), (1, 0)], lease_until=2))

        table.release_expired_leases(2)

        self.assertIsNone(table.get_owner((0, 0), 0))
        self.assertIsNone(table.get_edge_owner((0, 0), (1, 0), 1))


if __name__ == "__main__":
    unittest.main()
