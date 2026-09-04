Yes. Before writing the implementation, it's worth freezing the **software specification** for every file. That will prevent the project from becoming a collection of scripts that don't fit together.

Below is the requirements/specification I would use for the **Auction + Distributed Planning** version.

---

# 1. Final project structure

```text
amr-fleet/
│
├── main.py
├── config.py
├── requirements.txt
│
├── simulation/
│   ├── __init__.py
│   ├── warehouse.py
│   ├── simulator.py
│   └── metrics.py
│
├── robots/
│   ├── __init__.py
│   ├── state.py
│   ├── robot.py
│   └── robot_manager.py
│
├── planning/
│   ├── __init__.py
│   ├── astar.py
│   ├── reservation.py
│   ├── collision.py
│   └── deadlock.py
│
├── auction/
│   ├── __init__.py
│   ├── task.py
│   ├── bid.py
│   └── auction.py
│
├── communication/
│   ├── __init__.py
│   ├── message.py
│   └── network.py
│
├── visualization/
│   ├── __init__.py
│   └── renderer.py
│
└── tests/
    ├── test_warehouse.py
    ├── test_astar.py
    ├── test_auction.py
    ├── test_reservation.py
    ├── test_collision.py
    ├── test_deadlock.py
    └── test_robot.py
```

---

# 2. `config.py`

Central configuration. **No algorithmic logic here.**

### Requirements

Store:

* grid dimensions
* number of robots
* simulation timestep
* robot speed
* battery parameters
* auction parameters
* collision distance
* reservation horizon
* deadlock timeout
* random seed

### Example

```python
class Config:
    GRID_WIDTH = 30
    GRID_HEIGHT = 20

    NUM_ROBOTS = 3

    SIMULATION_DT = 0.1
    ROBOT_SPEED = 1.0

    INITIAL_BATTERY = 100.0

    RESERVATION_HORIZON = 20
    DEADLOCK_TIMEOUT = 5.0

    COLLISION_DISTANCE = 1.0

    AUCTION_INTERVAL = 1.0

    RANDOM_SEED = 42
```

Eventually you can move these to YAML, but don't bother initially.

---

# 3. `simulation/warehouse.py`

Responsible for the **physical environment**.

It knows:

* walls
* shelves
* walkable cells
* tasks
* obstacles

It should **not know how robots make decisions**.

---

## Class: `Warehouse`

```python
class Warehouse:
```

### Constructor

```python
__init__(grid)
```

Stores the map.

---

### Required methods

#### `is_valid_position(position)`

Checks whether coordinates are inside the warehouse.

```python
is_valid_position((x, y)) -> bool
```

---

#### `is_walkable(position)`

Checks whether a robot can occupy a cell.

```python
is_walkable((x, y)) -> bool
```

---

#### `get_neighbors(position)`

Returns possible adjacent cells.

```python
get_neighbors((x, y)) -> list[tuple]
```

Example:

```text
      ↑
      |
←──── X ────→
      |
      ↓
```

---

#### `add_obstacle(position)`

Dynamically blocks a location.

---

#### `remove_obstacle(position)`

Removes a dynamic obstacle.

---

#### `add_task(task)`

Adds a task to the warehouse.

---

#### `remove_task(task_id)`

Removes/completes a task.

---

#### `get_pending_tasks()`

Returns unassigned tasks.

---

#### `get_task(task_id)`

Returns a specific task.

---

# 4. `simulation/simulator.py`

This is the **world clock**.

It advances the simulation but should not make robot decisions.

---

## Class: `Simulator`

```python
class Simulator:
```

### Constructor

```python
__init__(
    warehouse,
    robots,
    network,
    reservation_table,
    metrics
)
```

---

### Methods

#### `step()`

Performs one simulation timestep.

Flow:

```text
Update environment
       ↓
Deliver messages
       ↓
Update robots
       ↓
Move robots
       ↓
Check collisions
       ↓
Update metrics
```

---

#### `run(steps)`

Runs simulation for a given number of steps.

---

#### `spawn_task(task)`

Adds a task.

---

#### `spawn_obstacle(position)`

Adds a dynamic obstacle.

---

#### `remove_obstacle(position)`

Removes an obstacle.

---

#### `is_finished()`

Returns whether all tasks are complete.

---

#### `reset()`

Resets simulation.

---

# 5. `simulation/metrics.py`

This is extremely important because your problem has a measurable success criterion.

---

## Class: `Metrics`

Track:

```text
collisions
tasks completed
total distance
waiting time
replanning count
deadlocks
completion time
```

### Constructor

```python
__init__()
```

---

### Methods

```python
start_simulation()
```

Records start time.

```python
end_simulation()
```

Records end time.

```python
record_collision(robot_a, robot_b)
```

```python
record_task_completed(task, robot)
```

```python
record_movement(robot, distance)
```

```python
record_wait(robot, duration)
```

```python
record_replan(robot)
```

```python
record_deadlock(robots)
```

---

### Important methods

```python
get_completion_time()
```

```python
get_average_task_time()
```

```python
get_collision_count()
```

```python
get_summary()
```

---

### Baseline comparison

Also:

```python
calculate_improvement(baseline_time, proposed_time)
```

Example:

```text
Baseline = 100 sec
Proposed = 75 sec

Improvement = 25%
```

---

# 6. `robots/state.py`

Contains **only robot state**.

Use a dataclass.

---

## Class: `RobotState`

```python
@dataclass
class RobotState:
```

### Fields

```python
robot_id: int
position: tuple
velocity: tuple
battery: float

current_task_id: int | None
path: list
path_index: int

status: str
```

Status could be:

```text
IDLE
AUCTIONING
PLANNING
MOVING
WAITING
BLOCKED
COMPLETED
CHARGING
```

---

### Methods

```python
update_position(position)
```

```python
update_velocity(velocity)
```

```python
consume_battery(amount)
```

```python
set_task(task_id)
```

```python
clear_task()
```

```python
set_path(path)
```

```python
clear_path()
```

```python
get_next_position()
```

---

# 7. `robots/robot.py`

This is probably the **most important class in the project**.

The `Robot` is an autonomous agent.

---

## Class: `Robot`

```python
class Robot:
```

### Constructor

```python
__init__(
    robot_id,
    start_position,
    warehouse,
    planner,
    network,
    reservation_table
)
```

---

## Responsibilities

The robot must be able to:

* understand its state
* receive tasks
* bid for tasks
* plan routes
* communicate with other robots
* request reservations
* detect conflicts
* resolve conflicts
* detect blockage
* replan
* move
* complete tasks

---

## Core methods

### `update()`

Main decision loop.

```text
receive messages
      ↓
update world knowledge
      ↓
task?
 ┌────┴────┐
NO        YES
 │          │
auction   plan
            ↓
       conflict?
       /      \
     yes       no
      ↓         ↓
   resolve     move
```

---

### `calculate_bid(task)`

Returns the robot's bid.

---

### `accept_task(task)`

Assigns a task to the robot.

---

### `plan_path()`

Calls A*.

---

### `request_reservation()`

Requests future space/time slots.

---

### `release_reservation()`

Releases reservations after passing.

---

### `broadcast_state()`

Shares:

```text
position
velocity
task
path
battery
status
```

---

### `receive_message(message)`

Processes messages from other robots.

---

### `detect_conflict()`

Checks whether its planned trajectory conflicts with another robot.

---

### `handle_conflict()`

Possible actions:

```text
WAIT
REROUTE
REPLAN
RELEASE_RESERVATION
```

---

### `move()`

Moves one simulation step.

---

### `is_task_complete()`

Checks pickup/dropoff status.

---

### `complete_task()`

Marks task complete.

---

### `handle_blockage()`

Triggered when an aisle/path becomes unavailable.

---

### `replan()`

Runs A* again.

---

# 8. `robots/robot_manager.py`

Useful for managing the fleet without becoming a **central decision-maker**.

---

## Class: `RobotManager`

```python
class RobotManager:
```

### Methods

```python
add_robot(robot)
```

```python
remove_robot(robot_id)
```

```python
get_robot(robot_id)
```

```python
get_all_robots()
```

```python
get_robot_states()
```

```python
update_all()
```

```python
get_active_robots()
```

The manager can **observe and organize**, but shouldn't decide:

> "Robot 2 must take Task 5."

That decision belongs to the distributed auction.

---

# 9. `planning/astar.py`

Handles **individual route planning**.

---

## Class: `AStarPlanner`

```python
class AStarPlanner:
```

### Constructor

```python
__init__(warehouse)
```

---

### Methods

```python
find_path(start, goal)
```

Main A* implementation.

---

```python
heuristic(a, b)
```

For a grid, Manhattan distance is appropriate:

```text
|x1-x2| + |y1-y2|
```

---

```python
get_neighbors(position)
```

Uses warehouse's walkability.

---

```python
reconstruct_path(came_from, current)
```

---

### Important

A* should initially know about **static obstacles**.

Later you can add:

```python
find_path(
    start,
    goal,
    reservations=None
)
```

so paths can consider other robots.

---

# 10. `planning/reservation.py`

This is responsible for **space-time reservations**.

---

## Class: `Reservation`

Represents:

```text
Robot 2
Position (10,5)
Time 42
```

Fields:

```python
robot_id
position
timestep
```

---

## Class: `ReservationTable`

### Methods

```python
reserve(robot_id, position, timestep)
```

---

```python
release(robot_id)
```

---

```python
is_reserved(position, timestep)
```

Returns:

```python
True / False
```

---

```python
get_owner(position, timestep)
```

Returns robot ID.

---

```python
get_robot_reservations(robot_id)
```

---

```python
can_reserve(robot_id, path)
```

Checks the complete trajectory.

---

```python
reserve_path(robot_id, path, start_time)
```

---

# 11. `planning/collision.py`

Responsible for **safety detection**.

---

## Class: `CollisionDetector`

### Methods

```python
distance(robot_a, robot_b)
```

---

```python
detect_collision(robot_a, robot_b)
```

---

```python
detect_all_collisions(robots)
```

---

```python
detect_vertex_conflict(path_a, path_b)
```

Example:

```text
R1 → X
R2 → X
```

---

```python
detect_edge_conflict(path_a, path_b)
```

Example:

```text
R1: A → B
R2: B → A
```

---

```python
predict_collision(robot_a, robot_b, horizon)
```

Looks ahead instead of only checking the current position.

---

# 12. `planning/deadlock.py`

Responsible for detecting situations where robots are waiting indefinitely.

---

## Class: `DeadlockDetector`

### Methods

```python
build_wait_graph(robots)
```

Example:

```text
R1 → R2
R2 → R3
R3 → R1
```

---

```python
detect_cycle(graph)
```

Returns whether a deadlock exists.

---

```python
detect_deadlocks(robots)
```

---

```python
select_robot_to_reroute(deadlocked_robots)
```

Selection criteria could include:

```text
lowest task priority
largest remaining path
lowest battery
longest waiting time
```

---

```python
resolve_deadlock(robots)
```

Possible result:

```text
R1 → reroute
R2 → continue
R3 → continue
```

---

# 13. `auction/task.py`

Defines warehouse tasks.

---

## Class: `Task`

```python
@dataclass
class Task:
```

Fields:

```python
task_id
pickup
dropoff
priority
created_time
deadline
status
assigned_robot_id
```

Status:

```text
PENDING
AUCTIONING
ASSIGNED
IN_PROGRESS
COMPLETED
FAILED
```

---

### Methods

```python
assign(robot_id)
```

```python
start()
```

```python
complete()
```

```python
cancel()
```

```python
is_available()
```

---

# 14. `auction/bid.py`

Defines bids.

---

## Class: `Bid`

Fields:

```python
robot_id
task_id
travel_cost
time_cost
battery_cost
congestion_cost
total_cost
timestamp
```

---

### Method

```python
calculate_total()
```

Example:

```text
Total cost =
travel
+ congestion
+ battery
- priority
```

---

# 15. `auction/auction.py`

This implements the actual **auction protocol**.

---

## Class: `Auction`

### Constructor

```python
__init__(network, robots)
```

---

### Methods

### `announce_task(task)`

Broadcast:

```text
TASK_AVAILABLE
```

---

### `collect_bids(task)`

Waits for bids.

---

### `submit_bid(bid)`

Adds a bid.

---

### `select_winner(bids)`

Selects the lowest valid bid.

---

### `broadcast_winner(task, robot_id)`

Broadcasts:

```text
TASK_ASSIGNED
```

---

### `run_auction(task)`

Complete auction:

```text
announce
   ↓
collect bids
   ↓
validate bids
   ↓
select winner
   ↓
broadcast result
```

---

### Important design point

For the prototype, `Auction` can coordinate the simulation.

But **don't let it become a hidden centralized planner**.

It should only handle the auction protocol.

It should NOT:

```text
❌ calculate everyone's routes
❌ move robots
❌ resolve every collision
❌ choose robot paths
```

---

# 16. `communication/message.py`

Defines all network messages.

---

## Enum: `MessageType`

```python
class MessageType(Enum):

    STATE = "STATE"

    TASK_AVAILABLE = "TASK_AVAILABLE"

    BID = "BID"

    TASK_ASSIGNED = "TASK_ASSIGNED"

    PATH_INTENT = "PATH_INTENT"

    RESERVATION_REQUEST = "RESERVATION_REQUEST"

    RESERVATION_GRANTED = "RESERVATION_GRANTED"

    RESERVATION_DENIED = "RESERVATION_DENIED"

    CONFLICT = "CONFLICT"

    DEADLOCK = "DEADLOCK"

    OBSTACLE = "OBSTACLE"

    TASK_COMPLETED = "TASK_COMPLETED"
```

---

## Class: `Message`

Fields:

```python
sender_id
message_type
timestamp
payload
```

---

### Methods

```python
to_dict()
```

```python
from_dict(data)
```

---

# 17. `communication/network.py`

This provides the communication abstraction.

Initially, make it an **in-memory P2P simulator**.

---

## Class: `Network`

### Methods

```python
register(robot)
```

---

```python
unregister(robot_id)
```

---

```python
send(sender_id, receiver_id, message)
```

---

```python
broadcast(sender_id, message)
```

---

```python
receive(robot_id)
```

---

```python
get_connected_robots(robot_id)
```

---

### Later

You can replace this implementation:

```text
Network
   ↓
In-memory
```

with:

```text
Network
   ↓
UDP
```

or:

```text
Network
   ↓
Zenoh
```

or:

```text
Network
   ↓
ROS2
```

without changing your `Robot` class.

That's why the abstraction is useful.

---

# 18. `visualization/renderer.py`

Initially this can be very simple.

---

## Class: `Renderer`

```python
class Renderer:
```

### Methods

```python
render_warehouse(warehouse)
```

---

```python
render_robots(robots)
```

---

```python
render_tasks(tasks)
```

---

```python
render_paths(robots)
```

---

```python
render_reservations(reservation_table)
```

---

```python
render_metrics(metrics)
```

---

```python
update()
```

---

Later replace this with:

```text
FastAPI
+
React
+
Three.js
```

without touching the coordination algorithms.

---

# 19. `main.py`

This should be extremely small.

Its job is simply to **assemble everything**.

Conceptually:

```python
def main():

    warehouse = create_warehouse()

    network = Network()

    reservation_table = ReservationTable()

    metrics = Metrics()

    planner = AStarPlanner(warehouse)

    robots = create_robots(
        warehouse,
        planner,
        network,
        reservation_table
    )

    auction = Auction(
        network,
        robots
    )

    simulator = Simulator(
        warehouse,
        robots,
        network,
        reservation_table,
        metrics
    )

    simulator.run()
```

`main.py` should **not contain your algorithms**.

---

# 20. The most important interaction

Here's how the classes communicate.

```text
                     Simulator
                         │
                         │ update()
                         ▼
                      Robot
                         │
            ┌────────────┼─────────────┐
            │            │             │
            ▼            ▼             ▼
         Auction        A*         Network
            │            │             │
            │            ▼             │
            │          Path             │
            │                          │
            └───────────┐  ┌───────────┘
                        ▼  ▼
                  Other Robots
                        │
                        ▼
                 CollisionDetector
                        │
                        ▼
                ReservationTable
                        │
                        ▼
                  DeadlockDetector
                        │
                        ▼
                  Robot decision
```

---

# 21. Complete robot decision flow

This is the behavior I'd ultimately implement:

```text
                         ROBOT UPDATE
                              │
                              ▼
                    Read incoming messages
                              │
                              ▼
                     Broadcast own state
                              │
                              ▼
                    Do I have a task?
                       /          \
                     NO            YES
                     │              │
                     ▼              ▼
              Participate       Do I have
              in auction?        a path?
                  │              /     \
                  │            NO       YES
                  │            │         │
                  │           A*         ▼
                  │            │      Check path
                  │            │      conflicts
                  │            │         │
                  │            │      conflict?
                  │            │       /     \
                  │            │     YES      NO
                  │            │      │         │
                  │            │      ▼         ▼
                  │            │   Resolve     Move
                  │            │      │
                  │            │      ▼
                  │            │    Replan
                  │            │
                  └────────────┘
                              │
                              ▼
                       Task completed?
                         /          \
                       NO            YES
                       │              │
                     Continue       Complete
                                      │
                                      ▼
                               New auction
```

---

# 22. Dependency rules

I'd enforce these rules while coding.

### `Warehouse`

Can know:

```text
map
obstacles
tasks
```

Cannot know:

```text
which robot should move
```

---

### `Robot`

Can know:

```text
own state
known robot states
tasks
map
reservations
```

Can decide:

```text
bid
path
wait
reroute
```

---

### `Auction`

Can know:

```text
tasks
bids
```

Can decide:

```text
winner
```

Cannot decide:

```text
robot movement
```

---

### `AStarPlanner`

Can know:

```text
map
start
goal
optional reservations
```

Returns:

```text
path
```

Nothing else.

---

### `ReservationTable`

Can know:

```text
robot
position
time
```

Decides:

```text
reserved / available
```

---

### `CollisionDetector`

Only detects:

```text
collision
conflict
future conflict
```

It should not decide what a robot does.

---

### `DeadlockDetector`

Detects:

```text
waiting cycles
```

and recommends/initiates:

```text
rerouting
```

---

# 23. Minimum viable version

Don't implement all of this immediately.

Your **MVP** should only require:

```text
Warehouse
    +
A*
    +
Robot
    +
Task
    +
Auction
    +
Network
    +
Simulator
```

Get this working:

```text
3 robots
   ↓
3 tasks
   ↓
auction
   ↓
robots get tasks
   ↓
A*
   ↓
robots move
   ↓
tasks completed
```

Then add:

```text
MVP
 ↓
Reservation
 ↓
Collision detection
 ↓
Deadlock
 ↓
Dynamic obstacles
 ↓
Task reassignment
 ↓
Metrics
 ↓
Dashboard
```

That ordering is important. **Don't start by implementing ROS2, ORCA, MQTT, React, or PyBullet.** First prove that the distributed algorithm works in a deterministic 2D simulation.

Once this core is stable, the same interfaces can be connected to ROS2/Zenoh and eventually Raspberry Pis/Jetsons.
