import copy
import unittest

from dashboard import Dashboard, RenderResult
from dashboard.snapshot import normalize_snapshot
from visualization.renderer import Renderer


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.renderer = Renderer()
        self.sample_snapshot = {
            "grid_size": (6, 6),
            "robots": [
                {
                    "robot_id": 1,
                    "position": (1, 1),
                    "status": "MOVING",
                    "battery": 92.5,
                    "current_task_id": 101,
                    "path": [(1, 1), (1, 2), (1, 3)],
                },
                {
                    "robot_id": 2,
                    "position": (4, 4),
                    "status": "WAITING",
                    "battery": 80.0,
                    "current_task_id": None,
                    "path": [],
                },
            ],
            "tasks": [
                {
                    "task_id": 101,
                    "status": "IN_PROGRESS",
                    "priority": 3,
                    "pickup": (1, 1),
                    "dropoff": (1, 3),
                    "assigned_robot_id": 1,
                },
                {
                    "task_id": 102,
                    "status": "COMPLETED",
                    "priority": 1,
                    "pickup": (0, 0),
                    "dropoff": (4, 4),
                    "assigned_robot_id": 2,
                },
            ],
            "paths": {
                1: [(1, 1), (1, 2), (1, 3)],
            },
            "reservations": {
                ((2, 2), 1): 1,
                ((3, 3), 2): 2,
            },
            "conflicts": [
                ("vertex", (2, 2), 1, 2),
            ],
            "obstacles": [(0, 5), (5, 0)],
            "metrics": {
                "collisions": 0,
                "deadlocks": 0,
                "tasks_completed": 1,
                "total_distance": 18.0,
                "waiting_time": 0.4,
                "replanning_count": 1,
                "completion_time": 12.0,
                "baseline_time": 20.0,
                "proposed_time": 12.0,
            },
        }

    # 1. Renderer accepts a valid fixed snapshot
    def test_renderer_accepts_valid_snapshot(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIsInstance(output, str)
        self.assertIsInstance(output, RenderResult)
        self.assertIn("ACE - AMR FLEET DASHBOARD", output)
        self.assertIn("Warehouse Grid", output)

    # 2. Renderer handles missing optional fields
    def test_renderer_handles_missing_optional_fields(self):
        empty_snapshot = {}
        output = self.renderer.render(empty_snapshot)
        self.assertIsInstance(output, str)
        self.assertIn("Warehouse Grid", output)
        self.assertIn("Fleet Status", output)

        partial_snapshot = {
            "robots": None,
            "tasks": None,
            "metrics": None,
            "conflicts": None,
            "obstacles": None,
            "reservations": None,
        }
        output_partial = self.renderer.render(partial_snapshot)
        self.assertIsInstance(output_partial, str)

    # 3. Renderer displays robot state information
    def test_renderer_displays_robot_state_information(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("R1", output)
        self.assertIn("R2", output)
        self.assertIn("(1, 1)", output)
        self.assertIn("(4, 4)", output)
        self.assertIn("MOVING", output)
        self.assertIn("WAITING", output)

    # 4. Renderer displays battery information
    def test_renderer_displays_battery_information(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("92.5%", output)
        self.assertIn("80.0%", output)

    # 5. Renderer displays active tasks
    def test_renderer_displays_active_tasks(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("Task #101", output)
        self.assertIn("Tasks Overview", output)

    # 6. Renderer displays planned paths
    def test_renderer_displays_planned_paths(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("Planned Path", output)
        self.assertIn("(1,2)", output.replace(" ", ""))

    # 7. Renderer distinguishes reservations from blocked cells
    def test_renderer_distinguishes_reservations_from_blocked_cells(self):
        snapshot = {
            "grid_size": (3, 3),
            "obstacles": [(0, 0)],
            "reservations": {((2, 2), 1): 1},
        }
        output = self.renderer.render(snapshot)
        # Blocked cell uses # and reservation cell uses ~
        self.assertIn("#", output)
        self.assertIn("~", output)
        # Legend explicitly documents distinction
        self.assertIn("[#] Blocked/Obstacle", output)
        self.assertIn("[~] Reservation", output)

    # 8. Renderer displays conflicts
    def test_renderer_displays_conflicts(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("Safety & Conflict Monitoring", output)
        self.assertIn("Active Conflicts Detected", output)
        self.assertIn("Vertex conflict", output)

    # 9. Renderer displays metrics
    def test_renderer_displays_metrics(self):
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("Collisions: 0", output)
        self.assertIn("Deadlocks: 0", output)
        self.assertIn("Replanning Count: 1", output)
        self.assertIn("18.0m", output)
        self.assertIn("0.40s", output)

    # 10. Renderer calculates/displays completion percentage where applicable
    def test_renderer_calculates_completion_percentage(self):
        output = self.renderer.render(self.sample_snapshot)
        # 1 completed out of 2 tasks = 50.0%
        self.assertIn("Completion Percentage: 50.0%", output)

        # Explicit completion percentage in metrics
        explicit_snapshot = {
            "metrics": {"completion_percentage": 75.0},
        }
        out_explicit = self.renderer.render(explicit_snapshot)
        self.assertIn("Completion Percentage: 75.0%", out_explicit)

    # 11. Renderer calculates/displays improvement percentage where applicable
    def test_renderer_calculates_improvement_percentage(self):
        # Baseline = 20.0s, Proposed = 12.0s -> improvement = (20 - 12) / 20 * 100 = 40.0%
        output = self.renderer.render(self.sample_snapshot)
        self.assertIn("Improvement Percentage: +40.00%", output)

        # Explicit improvement in metrics
        explicit_snapshot = {
            "metrics": {"improvement": 25.5},
        }
        out_explicit = self.renderer.render(explicit_snapshot)
        self.assertIn("Improvement Percentage: +25.50%", out_explicit)

    # 12. Rendering does not mutate the supplied snapshot
    def test_rendering_does_not_mutate_snapshot(self):
        original_copy = copy.deepcopy(self.sample_snapshot)
        _ = self.renderer.render(self.sample_snapshot)
        self.assertEqual(self.sample_snapshot, original_copy)

    # 13. Edge case: zero tasks and zero baseline time
    def test_zero_tasks_and_zero_baseline(self):
        snapshot = {
            "tasks": [],
            "metrics": {
                "tasks_completed": 0,
                "baseline_time": 0.0,
                "completion_time": 10.0,
            },
        }
        output = self.renderer.render(snapshot)
        self.assertIn("Improvement Percentage: 0.00%", output)

    # 14. Legacy renderer methods backward compatibility
    def test_legacy_renderer_methods(self):
        class DummyWarehouse:
            width = 3
            height = 3
            static_obstacles = {(1, 1)}
            dynamic_obstacles = set()

        class DummyState:
            position = (0, 0)
            path = [(0, 1)]

        class DummyRobot:
            robot_id = 99
            state = DummyState()

        dummy_wh = DummyWarehouse()
        dummy_rob = DummyRobot()
        r = Renderer(warehouse=dummy_wh, robots=[dummy_rob])

        wh_str = r.render_warehouse()
        self.assertIn("#", wh_str)
        self.assertEqual(r.render_robots(), {99: (0, 0)})
        self.assertEqual(r.render_paths(), {99: [(0, 1)]})

        update_dict = r.update()
        self.assertIn("warehouse", update_dict)
        self.assertIn("robots", update_dict)
        self.assertIn("metrics", update_dict)

    # 15. Sequential snapshots show moving robots and updating state
    def test_sequential_snapshots_show_robot_movement(self):
        r = Renderer()
        snapshot_t0 = {
            "grid_size": (5, 5),
            "timestep": 0,
            "robots": [{"id": 0, "position": (0, 0), "status": "MOVING", "path": [(0, 0), (1, 0), (2, 0)]}],
        }
        frame_0 = r.render(snapshot_t0)
        self.assertIn("(0, 0)", frame_0)
        self.assertIn("Step: 0", frame_0)

        snapshot_t1 = {
            "grid_size": (5, 5),
            "timestep": 1,
            "robots": [{"id": 0, "position": (1, 0), "status": "MOVING", "path": [(1, 0), (2, 0)]}],
        }
        frame_1 = r.render(snapshot_t1)
        self.assertIn("(1, 0)", frame_1)
        self.assertIn("Step: 1", frame_1)

    # 16. ANSI color rendering
    def test_ansi_color_rendering(self):
        r = Renderer(color=True)
        colored_output = r.render(self.sample_snapshot)
        self.assertIn("\033[", colored_output)
        self.assertIn("R1", colored_output)


if __name__ == "__main__":
    unittest.main()
