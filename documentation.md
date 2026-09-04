# ACE Technical Documentation

This document is the technical reference for the ACE AMR coordination project. It describes the current Python implementation, how it maps to the SIH requirements, and how to run and extend the simulation.

## 1. Problem Context

The full source problem statement is [`SIH_PS.md`](SIH_PS.md). It identifies SIH problem **SIH26123** from Bharat Electronics Limited under the Smart Automation theme: build a decentralized coordination and collision-avoidance framework for at least three AMRs in a dynamic warehouse.

The problem statement highlights three operational needs:

1. Robots should exchange position, localization, and movement intent without depending on a central server for core coordination.
2. The fleet should resolve real-time conflicts such as deadlocks, collisions, narrow intersections, choke points, and overlapping paths.
3. Task assignment and routes should adapt when an aisle or pickup location changes.

The expected demonstration also includes a fleet dashboard showing robot positions, activity, and battery status. The stated success criteria are zero inter-robot collisions and at least 20% lower total task completion time than a traditional stop-and-wait approach for overlapping paths.

ACE currently implements these requirements as a deterministic, in-process multi-robot simulation. Its `Network` class models peer-to-peer delivery locally; it is not a production wireless transport or a physical edge deployment.

## 2. Architecture

```text
Tasks
  |
  v
Auction <----> Network <----> Robots
                                |
                    +-----------+-----------+
                    v                       v
                A* Planner          Reservation Table
                    |                       |
                    +-----------+-----------+
                                v
                           Simulator
                                |
                 +--------------+--------------+
                 v                             v
              Metrics                 Dashboard / Reports
```

### Package Responsibilities

| Package or file | Responsibility |
| --- | --- |
| `auction/` | Task states, bid calculation, centralized auction helper, and distributed auction claim/acknowledgement flow. |
| `communication/` | `Message` serialization and an in-process `Network` with per-robot queues and broadcast delivery. |
| `planning/` | A* routes, vertex/edge reservations, collision checks, deadlock detection/recovery, and ORCA velocity guidance. |
| `robots/` | Robot state, task queues, bidding, message handling, route execution, charging, obstacle response, and reassignments. |
| `simulation/` | Warehouse state, timestep orchestration, collision/deadlock accounting, completion, and summary metrics. |
| `scenarios/` | Reusable crossing, intersection, deadlock, reservation, and benchmark setups. |
| `dashboard/` | Streamlit controls and read-only rendering of normalized simulation snapshots. |
| `tests/` | Behavioral contracts for safety, coordination, rendering, scenarios, and reproducibility. |

## 3. Simulation Lifecycle

`main.py` exposes `build_simulation(config=None)`, which creates a warehouse, network, reservation table, metrics collector, A* planner, robots, auction, and five sample tasks. It starts an auction for each pending task and returns a `Simulator` plus the robot list.

Each simulator step follows this order:

1. Expire old reservation entries and leases.
2. Synchronize robot clocks and ORCA settings.
3. Update each robot in priority order. Robots receive queued messages, process charging and battery state, observe local obstacles, broadcast state, and plan when needed.
4. Compute optional ORCA guidance for each online robot.
5. Move robots in priority order using an atomic occupancy guard. A robot must pass both physical occupancy and reservation checks.
6. Record physical overlaps and future path conflicts.
7. Complete tasks whose robot has reached its dropoff and release their reservations.
8. Detect deadlock cycles and invoke recovery for a selected robot.
9. Advance simulation time by `simulation_dt`.

`Simulator.run(steps=1000)` repeats this lifecycle until all work is finished or the step limit is reached, then returns the metrics summary. `Simulator.run_stop_and_wait()` is a reference mode that advances one robot at a time; the benchmark package uses an equivalent sequential baseline helper for controlled comparisons.

## 4. Task Allocation And Auctions

Tasks contain an identifier, pickup and dropoff coordinates, priority, creation time, and lifecycle status. Robots calculate bids using route-related cost, congestion, priority, workload, battery feasibility, and invalid-bid penalties.

With `Config.distributed_auction=True`, the auction announces a task through the network. Online robots evaluate it and exchange bid messages. The distributed winner uses claim and acknowledgement messages to avoid stale or conflicting assignments before the task is assigned. With distributed auctions disabled, the `Auction` helper runs the local auction directly.

When a robot becomes unavailable or cannot complete a task, it releases reservations and returns unfinished work to the auction pool. Completed tasks are not re-auctioned. A robot can also queue additional assigned tasks and start the next task after completing the current one.

## 5. Planning And Safety

### A* Planning

`planning/astar.py` computes grid routes through walkable warehouse cells. The robot supplies the current position, goal, reservations, known obstacles, and cost settings. Congestion and priority values influence route selection, while unreachable goals fail cleanly and release their tasks.

### Reservations

`ReservationTable` protects both:

- Vertex occupancy: two robots cannot reserve the same cell at the same timestep.
- Edge occupancy: two robots cannot swap cells across the same timestep.

Robots reserve a forward rolling horizon rather than their entire lifetime route. Reservations have a lease and are renewed as the robot moves. Expired reservations and explicit releases prevent stale plans from blocking the fleet.

### Physical Occupancy

Reservations are predictive, not the only safety layer. During movement, the simulator blocks positions occupied by robots that have not moved during the current tick and by offline robots. The collision detector then checks actual robot positions and records each newly active pair.

### ORCA

When `orca_enabled` is true, `Robot.prepare_orca()` computes local velocity guidance using nearby robots. In the current discrete simulator, the A* waypoint remains authoritative because arbitrary side steps could invalidate reservations. ORCA can approve the next waypoint or provide a safe local movement target; the reservation table remains the discrete movement authority.

## 6. Conflict And Deadlock Handling

Robots treat a denied reservation or occupied next cell as a wait condition. Waiting time and blockage time are tracked. Sustained blockage triggers replanning, and an invalid or impossible route can fail the current task so it can be released for reassignment.

`DeadlockDetector` builds a wait graph from robot dependencies. When a cycle is found, the simulator records the cycle once and calls the resolver. Recovery selects a robot according to the project priority rules, releases or changes its route, and attempts to break the cycle. The scenario modules and `tests/test_deadlock_scenarios.py` exercise this behavior directly.

The collision detector also supports future vertex conflicts, reverse-edge conflicts, and path conflict inspection. Geometric route intersection alone is not treated as a live collision: time-indexed reservations determine whether two robots actually contend for a cell or edge at the same timestep.

## 7. Communication Model

`communication.message.Message` contains:

| Field | Meaning |
| --- | --- |
| `sender_id` | Robot that created the message. |
| `message_type` | Enum value describing the protocol event. |
| `timestamp` | Sender-local simulation time or timestep. |
| `payload` | Event-specific dictionary. |

The current message types include state, task availability, bids, task assignment, path intent, reservation requests/grants/denials/releases/preemption, conflicts, deadlocks, obstacle detection/clearing, task completion, and distributed auction claim/acknowledgement events.

`Network.broadcast()` delivers a message to every registered peer except the sender. `Network.send()` delivers to one peer, and `Network.receive()` drains the receiver queue. This provides a deterministic local protocol model and makes message handling testable without sockets or external services.

## 8. Obstacles, Battery, And Availability

Robots observe dynamic obstacles within their configured Manhattan sensor radius. A newly detected obstacle is announced to peers, known routes are invalidated when necessary, and affected robots replan before entering blocked cells. Obstacles that make a task unreachable cause the task to be released rather than silently completed.

Battery decreases per movement. Robots transition through online, low-battery, going-to-charger, charging, offline, or discharged states according to their battery thresholds and charging station configuration. A robot that goes offline releases reservations and unfinished work, and it cannot win new bids. The dashboard exposes battery and availability state.

## 9. Dashboard

Launch the dashboard with:

```bash
python run_dashboard.py
```

The launcher starts `dashboard/app.py` through Streamlit on `localhost:8501`. The dashboard supports a live loop and clock-controlled simulation modes, warehouse configuration, scenario generation, task spawning, obstacle placement/removal, coordinate inspection, and reset controls.

The dashboard engine normalizes snapshots before rendering. Its views can include:

- Warehouse grid and obstacles.
- Robot positions, statuses, paths, battery, and availability.
- Active and completed tasks.
- Reservations and conflicts.
- Completion time, waiting time, replans, collisions, deadlocks, throughput, and improvement metrics.

The rendering layer is designed to consume snapshots without mutating the simulation input, which is covered by renderer tests.

## 10. Scenarios And Benchmarks

Scenario builders in `scenarios/` provide focused worlds for manual experiments and tests:

| Scenario | Purpose |
| --- | --- |
| `basic` | Minimal two-robot world. |
| `crossing` | Two paths approaching the same center cell. |
| `opposite_paths` | Head-on movement through a shared route. |
| `three_way_intersection` | Three robots contending for an intersection. |
| `four_way_intersection` | Four-way center intersection. |
| `deadlock` | Cyclic wait graph and recovery. |
| `benchmark` | Seeded task generation and baseline/distributed comparison. |

Run a benchmark from the repository root:

```bash
python benchmark.py --tasks 20 50 100 --seeds 42 43 44 45 46 --robots 3
```

Useful options are `--max-steps`, `--json`, and `--csv`. Each run records mode, seed, robot count, task count, completion time, throughput, collisions, deadlocks, waiting time, total distance, replans, and improvement. Aggregates include mean and median completion times, mean improvement, safety totals, and a `PASS`/`FAIL` status.

Print the exported report:

```bash
python benchmark_report.py benchmark_results.json
```

Benchmark task generation uses a local `random.Random(seed)` instance, so the same seed, robot count, task count, and step limit produce reproducible task inputs and results under the same code version.

## 11. Configuration Reference

All defaults below are defined by the frozen `Config` dataclass in `config.py`.

| Parameter | Default | Purpose |
| --- | ---: | --- |
| `grid_width`, `grid_height` | `30`, `20` | Warehouse grid dimensions. |
| `num_robots` | `3` | Number of robots in the sample simulation. |
| `simulation_dt` | `0.1` | Duration of one simulation step. |
| `robot_speed` | `1.0` | Robot movement speed. |
| `initial_battery` | `100.0` | Starting battery level. |
| `battery_consumption_per_move` | `1.0` | Battery cost per movement. |
| `offline_battery_cutoff` | `0.0` | Battery level at which a robot is discharged. |
| `charging_rate_per_step` | `1.0` | Battery restored per charging step. |
| `workload_penalty` | `5.0` | Bid cost for existing workload. |
| `reservation_horizon` | `20` | Forward reservation window. |
| `reservation_lease` | `20` | Reservation lease length. |
| `deadlock_timeout` | `5.0` | Deadlock-related waiting threshold. |
| `auction_interval` | `1.0` | Auction scheduling interval. |
| `distributed_auction` | `True` | Select distributed or direct auction behavior. |
| `obstacle_sensor_radius` | `2` | Local Manhattan sensing range. |
| `obstacle_safety_radius` | `0` | Additional obstacle clearance. |
| `random_seed` | `42` | Default experiment seed. |
| `congestion_penalty` | `2.0` | Route cost for congested cells or routes. |
| `priority_bonus` | `1.0` | Bid and scheduling priority adjustment. |
| `invalid_bid_penalty` | `1000000.0` | Cost assigned to infeasible bids. |
| `orca_enabled` | `True` | Enable local ORCA guidance. |
| `orca_neighbor_distance` | `3.0` | Distance used to consider nearby robots. |
| `orca_time_horizon` | `2.0` | ORCA prediction horizon. |
| `orca_robot_radius` | `0.5` | Robot radius for ORCA constraints. |
| `orca_max_speed` | `1.0` | Maximum ORCA speed. |

## 12. Testing And Extension

Run all tests:

```bash
python -m pytest -q
```

Focused examples:

```bash
python -m pytest tests/test_integration.py tests/test_simulation_safety.py -q
python -m pytest tests/test_benchmark.py -q
python -m pytest tests/test_deadlock_scenarios.py tests/test_collision.py -q
```

Recommended extension points:

- Add a new scenario builder under `scenarios/` and cover it with a focused test.
- Add message types and handling for new coordination events in `communication/message.py` and `robots/robot.py`.
- Replace or extend `Network` when integrating a real transport, while preserving the message contract.
- Add planner cost terms or alternate planners behind the robot planning interface.
- Add metrics fields only when the simulator and dashboard snapshot normalization are updated together.
- Add dashboard controls through `dashboard/app.py` and keep rendering logic read-only.

## 13. Troubleshooting

### Import errors

Run commands from the repository root and activate the virtual environment before installing `requirements.txt`.

### Dashboard does not open

Open `http://localhost:8501` manually. If the port is already in use, pass another Streamlit port:

```bash
python run_dashboard.py --server.port=8502
```

### A simulation does not finish

Increase the run limit, inspect waiting/deadlock/replan metrics, and use the focused scenario tests to isolate the behavior. A bounded run can return a partial summary when its step limit is reached.

### Benchmark status is `FAIL`

Inspect collisions, deadlocks, improvement, and completion time in the JSON or formatted report. `FAIL` means the aggregate did not satisfy both project thresholds; it does not identify one single cause.

## 14. Scope And Limitations

- The network is an in-process deterministic model, not a Wi-Fi, ROS, DDS, or hardware transport.
- The warehouse is represented as a discrete grid; physical kinematics and sensor noise are simplified.
- ORCA is advisory during the discrete movement phase and does not replace reservation-based grid planning.
- Benchmark performance depends on task seed, task count, robot count, step limit, and code version.
- Passing tests and benchmark status are simulation evidence, not a safety certification for physical AMRs.
