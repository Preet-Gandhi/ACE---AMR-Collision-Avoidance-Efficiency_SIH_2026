import random
import unittest

from dashboard.warehouse_env import WarehouseEnvironment
from planning.reservation import ReservationTable


class SimulationSafetyTests(unittest.TestCase):
    def test_four_delivery_slots_are_used_before_reuse(self):
        env = WarehouseEnvironment(num_robots=3)
        pickups = [(1, 4), (4, 4), (9, 4), (12, 4)]
        tasks = [env.spawn_task(p) for p in pickups]
        self.assertEqual(len({task.dropoff for task in tasks}), 4)
        self.assertEqual(set(task.dropoff for task in tasks), set(env.DROPOFF_CELLS))

    def test_reservation_table_blocks_reverse_edge(self):
        table = ReservationTable()
        self.assertTrue(table.reserve_path(1, [(0, 0), (1, 0)], start_time=0))
        self.assertFalse(table.can_reserve(2, [(1, 0), (0, 0)], start_time=0))
        self.assertEqual(table.get_edge_owner((0, 0), (1, 0), 1), 1)

    def test_dashboard_simulation_has_no_physical_overlap(self):
        random.seed(42)
        env = WarehouseEnvironment(3)
        tasks = env.randomize_pickups(20)
        for _ in range(1000):
            if all(task.is_finished() for task in tasks):
                break
            env.step()
            positions = [robot.state.position for robot in env.robots]
            self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(env.metrics.collisions, 0)

    def test_renderer_is_state_synchronised(self):
        from dashboard.snapshot import normalize_snapshot
        from dashboard.svg_view import SvgWarehouseRenderer

        env = WarehouseEnvironment(1)
        env.spawn_task((2, 4))
        svg = SvgWarehouseRenderer.render_svg(normalize_snapshot(env.get_snapshot()))
        self.assertNotIn("animateMotion", svg)


if __name__ == "__main__":
    unittest.main()
