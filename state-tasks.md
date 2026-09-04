Person 1: Dynamic Obstacles and Reassignment
Own these files:
- simulation/warehouse.py
- communication/message.py
- robots/robot.py
- New tests under tests/test_obstacles.py and tests/test_reassignment.py
Implement:
- OBSTACLE_DETECTED message type.
- Dynamic obstacle broadcast.
- Robot path validity checks.
- Release of invalidated reservations.
- A* replanning around blocked cells.
- Waiting threshold for unreachable tasks.
- Task failure and reassignment.
- Re-broadcast of TASK_AVAILABLE.
- New robot acceptance of a released task.
Do not modify:
- planning/reservation.py
- planning/collision.py
- planning/deadlock.py
- simulation/simulator.py
Required interface:
robot.handle_obstacle(position)
robot.is_path_valid()
robot.fail_current_task()
auction.release_task(task)
If simulator integration is required, add a new callback or message-based mechanism instead of editing simulation/simulator.py.
Acceptance criteria:
- A robot detects a blocked cell on its current route.
- Its old reservations are released.
- It successfully replans when an alternate path exists.
- An unreachable task is released and reassigned.
- No collision occurs.
Person 2: Deadlock Detection and Recovery
Own these files:
- planning/deadlock.py
- New tests under tests/test_deadlock_scenarios.py
- New scenarios:
  - scenarios/deadlock.py
  - scenarios/three_way_intersection.py
Implement:
- Wait-for graph construction from reservation conflicts.
- Cycle detection.
- Priority-based reroute selection.
- Forced reservation release for the selected robot.
- Deadlock resolution result reporting.
Required interface:
deadlock_detector.build_wait_graph(robots)
deadlock_detector.detect_deadlocks(robots)
deadlock_detector.select_robot_to_reroute(robots)
deadlock_detector.resolve_deadlock(robots)
Return a structured result containing:
{
    "detected": bool,
    "robots": list[int],
    "rerouted_robot_id": int | None,
}
Do not modify:
- robots/robot.py
- simulation/simulator.py
- planning/reservation.py
Acceptance criteria:
- A deliberate cycle such as R1 -> R2 -> R3 -> R1 is detected.
- Exactly one robot is selected for rerouting.
- Its reservations are released.
- The fleet eventually completes the scenario.
- Collisions remain zero.