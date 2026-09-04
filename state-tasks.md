The project is currently at a stable reservation-driven MVP stage.

**Current State**

- `17` tests pass.
- `python main.py` runs successfully.
- The demo supports:
  - 3 robots
  - 5 tasks
  - Auction-based assignment
  - A* path planning
  - Time-indexed reservations
  - Vertex conflict detection
  - Edge-swap conflict detection
  - Priority-aware reservation attempts
  - Waiting and replanning after reservation loss
  - Collision and movement metrics
  - Basic text rendering
- The demo currently reports:
  - `5` completed tasks
  - `0` collisions

Important existing files:

- [main.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/main.py): demo assembly and execution.
- [robots/robot.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/robots/robot.py): robot behavior.
- [simulation/simulator.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/simulation/simulator.py): simulation clock and coordination loop.
- [planning/reservation.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/planning/reservation.py): authoritative space-time reservations.
- [planning/collision.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/planning/collision.py): current and future conflict detection.
- [planning/deadlock.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/planning/deadlock.py): basic wait-graph and cycle detection.
- [visualization/renderer.py](C:/Users/prate/Desktop/test/ACE---AMR-Collision-Avoidance-Efficiency_SIH_2026/visualization/renderer.py): read-only text renderer.

Not yet complete:

- Dynamic obstacle recovery
- Task reassignment after failure
- Fully integrated deadlock recovery tests
- Baseline/distributed benchmark comparison
- Real dashboard
- UDP or ROS2 communication

## Shared Contracts

Before parallel work begins, freeze these rules:

- Coordinates are `(x, y)`.
- A path includes the starting position.
- Reservation keys are `(position, timestep)`.
- `ReservationTable.reserve_path()` is atomic.
- A robot may have one active task and multiple queued tasks.
- `Robot.update()` remains the robot decision entry point.
- `Simulator.step()` remains the only simulation clock.
- Network methods remain:
  - `send(sender_id, receiver_id, message)`
  - `broadcast(sender_id, message)`
  - `receive(robot_id)`
- Existing tests must continue to pass.
- New behavior must be tested with deterministic scenarios.
- Contributors must not edit another workstream’s owned files.

## Four-Person Work Split

### Person 1: Dynamic Obstacles and Reassignment

Own these files:

- `simulation/warehouse.py`
- `communication/message.py`
- `robots/robot.py`
- New tests under `tests/test_obstacles.py` and `tests/test_reassignment.py`

Implement:

- `OBSTACLE_DETECTED` message type.
- Dynamic obstacle broadcast.
- Robot path validity checks.
- Release of invalidated reservations.
- A* replanning around blocked cells.
- Waiting threshold for unreachable tasks.
- Task failure and reassignment.
- Re-broadcast of `TASK_AVAILABLE`.
- New robot acceptance of a released task.

Do not modify:

- `planning/reservation.py`
- `planning/collision.py`
- `planning/deadlock.py`
- `simulation/simulator.py`

Required interface:

```python
robot.handle_obstacle(position)
robot.is_path_valid()
robot.fail_current_task()
auction.release_task(task)
```

If simulator integration is required, add a new callback or message-based mechanism instead of editing `simulation/simulator.py`.

Acceptance criteria:

- A robot detects a blocked cell on its current route.
- Its old reservations are released.
- It successfully replans when an alternate path exists.
- An unreachable task is released and reassigned.
- No collision occurs.

### Person 2: Deadlock Detection and Recovery

Own these files:

- `planning/deadlock.py`
- New tests under `tests/test_deadlock_scenarios.py`
- New scenarios:
  - `scenarios/deadlock.py`
  - `scenarios/three_way_intersection.py`

Implement:

- Wait-for graph construction from reservation conflicts.
- Cycle detection.
- Priority-based reroute selection.
- Forced reservation release for the selected robot.
- Deadlock resolution result reporting.

Required interface:

```python
deadlock_detector.build_wait_graph(robots)
deadlock_detector.detect_deadlocks(robots)
deadlock_detector.select_robot_to_reroute(robots)
deadlock_detector.resolve_deadlock(robots)
```

Return a structured result containing:

```python
{
    "detected": bool,
    "robots": list[int],
    "rerouted_robot_id": int | None,
}
```

Do not modify:

- `robots/robot.py`
- `simulation/simulator.py`
- `planning/reservation.py`

Acceptance criteria:

- A deliberate cycle such as `R1 -> R2 -> R3 -> R1` is detected.
- Exactly one robot is selected for rerouting.
- Its reservations are released.
- The fleet eventually completes the scenario.
- Collisions remain zero.

### New Task for Person 3: Benchmark Reporting and Analysis
Improve the benchmark output so it produces an evaluation report suitable for the project presentation.
Own only:
- simulation/metrics.py
- scenarios/benchmark.py
- benchmark.py
- tests/test_benchmark.py
- New file: benchmark_report.py
Do not modify:
- robots/
- planning/
- communication/
- simulation/simulator.py
- dashboard/
- visualization/
Implement:
- Run all configurations:
  - 3 robots
  - 20, 50, 100 tasks
  - Seeds 42, 43, 44, 45, 46
- Calculate per configuration:
  - Mean completion time
  - Median completion time
  - Mean throughput
  - Mean waiting time
  - Mean travel distance
  - Mean replans
  - Total collisions
  - Total deadlocks
  - Mean improvement
- Report pass/fail:
  - collision_count == 0
  - improvement >= 20%
- Export results to:
  - benchmark_results.json
  - benchmark_results.csv
- Add CLI options:
python benchmark.py --tasks 20 50 100 --seeds 42 43 44 45 46
python benchmark_report.py benchmark_results.json
Required report format:
AMR BENCHMARK REPORT
Robots: 3
Tasks: 20
Seeds: 5

Baseline mean time:  ...
Distributed mean time: ...
Mean improvement:      ...%
Total collisions:      0
Total deadlocks:       0
Status: PASS
Tests must verify:
- Same seed produces identical results.
- Aggregation calculates correct mean and median.
- JSON and CSV contain all required fields.
- A scenario with less than 20% improvement reports FAIL.
- Any collision causes the safety status to report FAIL.
- Existing tests remain passing.
Final verification:
python -m pytest -q
python benchmark.py --tasks 20 --seeds 42 43 44 45 46
python benchmark_report.py benchmark_results.json
Do not commit generated benchmark_results.json or .csv unless the team explicitly wants benchmark artifacts versioned.

### Person 4: Dashboard and Visualization

Own these files:

- `visualization/renderer.py`
- `visualization/__init__.py`
- `dashboard/`
- New tests under `tests/test_renderer.py`

Implement:

- Warehouse grid display.
- Robot positions.
- Robot status.
- Battery.
- Active task.
- Planned paths.
- Reservations.
- Conflicts.
- Blocked aisles.
- Metrics summary.
- Completion percentage.
- Improvement percentage.

Use a read-only snapshot interface:

```python
renderer.render(snapshot)
```

Snapshot format:

```python
{
    "robots": [...],
    "tasks": [...],
    "paths": {...},
    "reservations": {...},
    "conflicts": [...],
    "obstacles": [...],
    "metrics": {...},
}
```

Do not modify:

- `robots/robot.py`
- `simulation/simulator.py`
- `planning/*`
- `auction/*`

The renderer must tolerate missing optional fields and must never mutate simulation state.

Acceptance criteria:

- Renderer can display a fixed scenario snapshot.
- Robot states and metrics are visible.
- Reservations and blocked cells are distinguishable.
- Rendering tests do not require a browser or external service initially.

## Git Workflow

Each person should work on a separate branch:

```text
codex/dynamic-obstacles
codex/deadlock-recovery
codex/benchmarking
codex/dashboard
```

Each contributor should:

- Modify only owned files.
- Add tests beside the feature.
- Run `python -m pytest -q`.
- Avoid formatting unrelated files.
- Commit only their workstream.
- Rebase or merge from the shared branch before integration.
- Report any required interface change before modifying another owner’s files.

Recommended merge order:

1. Deadlock recovery
2. Dynamic obstacles and reassignment
3. Benchmarking
4. Dashboard

The dashboard and benchmark branches should consume stable interfaces rather than change coordination behavior. After merging each branch:

```powershell
python -m pytest -q
python main.py
```

The first milestone should be reached when the controlled crossing, opposing-path, four-way intersection, deadlock, and blocked-aisle scenarios all complete with zero collisions.