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

    # 17. Custom obstacle at (0, 0) rendered as obstacle, not rack
    def test_custom_obstacle_at_origin_rendered_as_obstacle_not_rack(self):
        from dashboard.svg_view import SvgWarehouseRenderer

        snapshot = {
            "grid_size": (10, 10),
            "shelves": [(2, 2), (2, 3)],
            "custom_obstacles": [(0, 0)],
            "dropoff_cells": [(5, 9), (6, 9)],
            "dropoff_station": (5, 9),
            "robots": [],
        }
        normalized = normalize_snapshot(snapshot)
        self.assertEqual(normalized.custom_obstacles, ((0, 0),))
        self.assertEqual(normalized.shelves, ((2, 2), (2, 3)))

        svg_out = SvgWarehouseRenderer.render_svg(normalized)
        # Hazard styling must be present for (0, 0)
        self.assertIn("url(#hazard-stripes)", svg_out)
        self.assertIn("⚠️", svg_out)
        # Ensure (0, 0) coordinate is labeled
        self.assertIn("X=0", svg_out)
        self.assertIn("Y=0", svg_out)

    # 18. WarehouseEnvironment cell status check and dropoff reachability
    def test_warehouse_env_cell_status_and_reachability(self):
        from dashboard.warehouse_env import WarehouseEnvironment

        env = WarehouseEnvironment(num_robots=2)

        # (0, 0) is a valid open aisle cell
        status_0_0, _ = env.check_cell_status((0, 0))
        self.assertEqual(status_0_0, "AVAILABLE")

        # Shelf rack
        status_rack, _ = env.check_cell_status(env.SHELF_BLOCKS[0])
        self.assertEqual(status_rack, "RACK")

        # Dropoff station
        status_drop, _ = env.check_cell_status(env.DROPOFF_STATION)
        self.assertEqual(status_drop, "DROPOFF")

        # Place obstacle at (0, 0)
        success, msg = env.add_custom_obstacle((0, 0))
        self.assertTrue(success)
        self.assertIn((0, 0), env.custom_obstacles)

        # Now (0, 0) is an existing obstacle
        status_now, _ = env.check_cell_status((0, 0))
        self.assertEqual(status_now, "EXISTING_OBSTACLE")

        # Remove obstacle
        removed = env.remove_custom_obstacle((0, 0))
        self.assertTrue(removed)
        self.assertNotIn((0, 0), env.custom_obstacles)

    # 19. Rack-facing pickup locations are strictly adjacent to shelf racks
    def test_rack_pickup_cells_adjacent_to_shelves(self):
        from dashboard.warehouse_env import WarehouseEnvironment

        env = WarehouseEnvironment(num_robots=2)
        shelves_set = set(env.SHELF_BLOCKS)
        dropoffs_set = set(env.DROPOFF_CELLS)

        self.assertTrue(len(env.RACK_PICKUP_CELLS) > 0)
        for px, py in env.RACK_PICKUP_CELLS:
            self.assertNotIn((px, py), shelves_set)
            self.assertNotIn((px, py), dropoffs_set)
            adjacent_to_shelf = any(
                (px + dx, py + dy) in shelves_set
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
            )
            self.assertTrue(adjacent_to_shelf, f"Pickup cell {(px, py)} must be adjacent to a shelf rack.")

    # 20. Reset completely clears custom obstacles and restores clean environment
    def test_warehouse_env_reset_clears_all(self):
        from dashboard.warehouse_env import WarehouseEnvironment

        env = WarehouseEnvironment(num_robots=2)
        env.add_custom_obstacle((0, 0))
        env.add_custom_obstacle((1, 0))
        self.assertEqual(len(env.custom_obstacles), 2)

        env.reset()
        self.assertEqual(len(env.custom_obstacles), 0)
        self.assertEqual(env.simulator.time, 0.0)

    # 21. Real delivery cycle: pickup -> transport package -> dropoff -> complete -> idle
    def test_delivery_cycle_pickup_transport_dropoff(self):
        from dashboard.warehouse_env import WarehouseEnvironment
        from dashboard.snapshot import normalize_snapshot
        from dashboard.svg_view import SvgWarehouseRenderer

        env = WarehouseEnvironment(num_robots=1)
        pickup_pos = (2, 4)
        env.spawn_task(pickup_pos)
        r = env.robots[0]

        # Initially heading to pickup, no package yet
        snap_0 = env.get_snapshot()
        norm_0 = normalize_snapshot(snap_0)
        r_view_0 = norm_0.robots[0]
        self.assertFalse(r_view_0.has_package)
        self.assertEqual(r_view_0.task_stage, "GOING_TO_PICKUP")

        # Step until robot reaches pickup
        max_steps = 40
        reached_pickup = False
        transported = False
        completed = False

        for _ in range(max_steps):
            env.step()
            snap = env.get_snapshot()
            norm = normalize_snapshot(snap)
            r_view = norm.robots[0]

            if r.state.position == pickup_pos:
                reached_pickup = True
                self.assertTrue(r_view.has_package)

            if r_view.task_stage == "TRANSPORTING":
                transported = True
                self.assertTrue(r_view.has_package)
                # Verify SVG contains package indicator 📦
                svg_transport = SvgWarehouseRenderer.render_svg(norm)
                self.assertIn("📦", svg_transport)

            if r.state.status == "IDLE" and reached_pickup:
                completed = True
                self.assertFalse(r_view.has_package)
                self.assertEqual(r_view.task_stage, "IDLE")
                break

        self.assertTrue(reached_pickup, "Robot should reach pickup.")
        self.assertTrue(transported, "Robot should transition to TRANSPORTING.")
        self.assertTrue(completed, "Robot should complete task at dropoff and become IDLE.")
        self.assertEqual(env.metrics.get_summary()["tasks_completed"], 1)

    # 22. Edge dropoff cells strictly exclude corners and shelves
    def test_edge_dropoff_cells_exclude_corners_and_shelves(self):
        from dashboard.warehouse_env import WarehouseEnvironment

        env = WarehouseEnvironment(num_robots=2)
        expected_corners = {(0, 0), (0, env.HEIGHT - 1), (env.WIDTH - 1, 0), (env.WIDTH - 1, env.HEIGHT - 1)}
        self.assertEqual(env.CORNERS, expected_corners)

        for corner in env.CORNERS:
            self.assertNotIn(corner, env.EDGE_DROPOFF_CELLS, f"Corner {corner} must not be in edge dropoffs.")

        for cell in env.EDGE_DROPOFF_CELLS:
            self.assertNotIn(cell, env.SHELF_BLOCKS, f"Dropoff {cell} must not be a shelf.")
            # Must be on perimeter
            x, y = cell
            is_on_edge = (x == 0 or x == env.WIDTH - 1 or y == 0 or y == env.HEIGHT - 1)
            self.assertTrue(is_on_edge, f"Cell {cell} should be on the grid perimeter.")

    # 23. Dynamic scenario generation randomized tasks and finish detection
    def test_scenario_generation_and_finish_detection(self):
        from dashboard.warehouse_env import WarehouseEnvironment

        env = WarehouseEnvironment(num_robots=3)
        tasks = env.generate_scenario(min_tasks=1, max_tasks=3)
        self.assertGreaterEqual(len(tasks), 1)
        self.assertLessEqual(len(tasks), 3)

        for t in tasks:
            self.assertNotIn(t.pickup, env.CORNERS)
            self.assertNotIn(t.dropoff, env.CORNERS)
            self.assertNotIn(t.pickup, env.SHELF_BLOCKS)
            self.assertNotIn(t.dropoff, env.SHELF_BLOCKS)

        self.assertFalse(env.is_scenario_finished())

    # 24. Pickup marker lifecycle: unpicked -> picked up -> completed
    def test_pickup_marker_lifecycle_in_svg(self):
        from dashboard.warehouse_env import WarehouseEnvironment
        from dashboard.snapshot import normalize_snapshot
        from dashboard.svg_view import SvgWarehouseRenderer

        env = WarehouseEnvironment(num_robots=1)
        pickup_pos = (2, 4)
        env.spawn_task(pickup_pos)

        # 1. Unpicked: should have "P1" in SVG
        snap1 = normalize_snapshot(env.get_snapshot())
        svg1 = SvgWarehouseRenderer.render_svg(snap1)
        self.assertIn("P1", svg1)
        self.assertNotIn("P1📦", svg1)

        # Step until picked up
        for _ in range(30):
            env.step()
            snap = normalize_snapshot(env.get_snapshot())
            if snap.robots[0].has_package:
                # 2. Picked up: should have "P1📦" in SVG
                svg_picked = SvgWarehouseRenderer.render_svg(snap)
                self.assertIn("P1📦", svg_picked)
                break

        # Step until finished
        for _ in range(50):
            env.step()
            snap = normalize_snapshot(env.get_snapshot())
            if snap.robots[0].status == "IDLE":
                # 3. Finished: pickup badge cleared from floor
                svg_done = SvgWarehouseRenderer.render_svg(snap)
                self.assertNotIn("P1📦", svg_done)
                break

    # 25. Distinct path colors and marker arrows rendered per robot
    def test_distinct_robot_path_colors(self):
        from dashboard.warehouse_env import WarehouseEnvironment
        from dashboard.snapshot import normalize_snapshot
        from dashboard.svg_view import SvgWarehouseRenderer

        env = WarehouseEnvironment(num_robots=3)
        env.generate_scenario(min_tasks=3, max_tasks=3)
        snap = normalize_snapshot(env.get_snapshot())
        svg = SvgWarehouseRenderer.render_svg(snap)

        # Check arrow markers exist in defs
        self.assertIn('id="path-arrow-0"', svg)
        self.assertIn('id="path-arrow-1"', svg)
        self.assertIn('id="path-arrow-2"', svg)


if __name__ == "__main__":
    unittest.main()

