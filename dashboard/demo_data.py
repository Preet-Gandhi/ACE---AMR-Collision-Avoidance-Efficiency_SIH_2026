from __future__ import annotations

from typing import Any, Dict, List


def get_fixed_demo_snapshot() -> Dict[str, Any]:
    """Returns a rich, fixed demonstration snapshot of the warehouse AMR fleet."""
    return {
        "grid_size": (12, 8),
        "timestep": 4,
        "time": 4.2,
        "obstacles": [
            # Shelf rack rows / blocked aisles
            (2, 1), (2, 2), (2, 3), (2, 5), (2, 6),
            (5, 1), (5, 2), (5, 3), (5, 5), (5, 6),
            (8, 1), (8, 2), (8, 3), (8, 5), (8, 6),
            (4, 4),  # Dynamic blocked aisle
        ],
        "robots": [
            {
                "robot_id": 1,
                "position": (3, 3),
                "status": "MOVING",
                "battery": 94.0,
                "current_task_id": 101,
                "path": [(3, 3), (3, 4), (3, 5), (4, 5), (5, 5)],
            },
            {
                "robot_id": 2,
                "position": (6, 4),
                "status": "WAITING",
                "battery": 78.5,
                "current_task_id": 102,
                "path": [(6, 4), (7, 4), (8, 4)],
            },
            {
                "robot_id": 3,
                "position": (9, 2),
                "status": "MOVING",
                "battery": 88.0,
                "current_task_id": 103,
                "path": [(9, 2), (9, 3), (9, 4), (10, 4)],
            },
            {
                "robot_id": 4,
                "position": (1, 4),
                "status": "IDLE",
                "battery": 98.0,
                "current_task_id": None,
                "path": [],
            },
        ],
        "tasks": [
            {"task_id": 101, "status": "IN_PROGRESS", "priority": 3, "pickup": (1, 1), "dropoff": (5, 5), "assigned_robot_id": 1},
            {"task_id": 102, "status": "IN_PROGRESS", "priority": 2, "pickup": (6, 1), "dropoff": (10, 4), "assigned_robot_id": 2},
            {"task_id": 103, "status": "IN_PROGRESS", "priority": 4, "pickup": (9, 1), "dropoff": (11, 7), "assigned_robot_id": 3},
            {"task_id": 104, "status": "COMPLETED", "priority": 1, "pickup": (0, 0), "dropoff": (3, 2), "assigned_robot_id": 1},
            {"task_id": 105, "status": "COMPLETED", "priority": 2, "pickup": (4, 0), "dropoff": (7, 3), "assigned_robot_id": 2},
            {"task_id": 106, "status": "PENDING", "priority": 1, "pickup": (1, 7), "dropoff": (9, 7), "assigned_robot_id": None},
        ],
        "paths": {
            1: [(3, 3), (3, 4), (3, 5), (4, 5), (5, 5)],
            2: [(6, 4), (7, 4), (8, 4)],
            3: [(9, 2), (9, 3), (9, 4), (10, 4)],
            4: [],
        },
        "reservations": {
            ((3, 4), 5): 1,
            ((3, 5), 6): 1,
            ((7, 4), 7): 2,
            ((8, 4), 8): 2,
            ((9, 3), 5): 3,
            ((9, 4), 6): 3,
        },
        "conflicts": [],
        "metrics": {
            "collisions": 0,
            "deadlocks": 0,
            "tasks_completed": 2,
            "total_tasks": 6,
            "total_distance": 38.5,
            "waiting_time": 1.2,
            "replanning_count": 1,
            "baseline_time": 42.0,
            "completion_time": 31.8,
            "improvement": 24.29,
        },
    }


def get_demo_timeline() -> List[Dict[str, Any]]:
    """Returns an animated multi-step timeline of snapshots for interactive playback."""
    base = get_fixed_demo_snapshot()
    steps = []

    # Frame 0: Start of movement
    f0 = dict(base)
    f0["timestep"] = 0
    f0["time"] = 0.0
    f0["robots"] = [
        {"robot_id": 1, "position": (3, 1), "status": "MOVING", "battery": 99.0, "current_task_id": 101, "path": [(3, 1), (3, 2), (3, 3), (3, 4), (3, 5)]},
        {"robot_id": 2, "position": (6, 2), "status": "MOVING", "battery": 85.0, "current_task_id": 102, "path": [(6, 2), (6, 3), (6, 4), (7, 4)]},
        {"robot_id": 3, "position": (9, 1), "status": "MOVING", "battery": 92.0, "current_task_id": 103, "path": [(9, 1), (9, 2), (9, 3), (9, 4)]},
        {"robot_id": 4, "position": (1, 4), "status": "IDLE", "battery": 98.0, "current_task_id": None, "path": []},
    ]
    f0["conflicts"] = []
    steps.append(f0)

    # Frame 1: Mid-travel
    f1 = dict(base)
    f1["timestep"] = 1
    f1["time"] = 1.0
    f1["robots"] = [
        {"robot_id": 1, "position": (3, 2), "status": "MOVING", "battery": 98.0, "current_task_id": 101, "path": [(3, 2), (3, 3), (3, 4), (3, 5)]},
        {"robot_id": 2, "position": (6, 3), "status": "MOVING", "battery": 83.0, "current_task_id": 102, "path": [(6, 3), (6, 4), (7, 4)]},
        {"robot_id": 3, "position": (9, 2), "status": "MOVING", "battery": 90.0, "current_task_id": 103, "path": [(9, 2), (9, 3), (9, 4)]},
        {"robot_id": 4, "position": (1, 4), "status": "IDLE", "battery": 98.0, "current_task_id": None, "path": []},
    ]
    f1["conflicts"] = []
    steps.append(f1)

    # Frame 2: Conflict detected (potential vertex conflict resolved by reservation table)
    f2 = dict(base)
    f2["timestep"] = 2
    f2["time"] = 2.0
    f2["robots"] = [
        {"robot_id": 1, "position": (3, 3), "status": "MOVING", "battery": 96.0, "current_task_id": 101, "path": [(3, 3), (3, 4), (3, 5)]},
        {"robot_id": 2, "position": (6, 4), "status": "WAITING", "battery": 80.0, "current_task_id": 102, "path": [(6, 4), (7, 4)]},
        {"robot_id": 3, "position": (9, 3), "status": "MOVING", "battery": 89.0, "current_task_id": 103, "path": [(9, 3), (9, 4)]},
        {"robot_id": 4, "position": (1, 4), "status": "IDLE", "battery": 98.0, "current_task_id": None, "path": []},
    ]
    f2["conflicts"] = [
        ("vertex", (7, 4), 3, 2),
    ]
    steps.append(f2)

    # Frame 3: Conflict resolved via waiting & reservation priority
    f3 = dict(base)
    f3["timestep"] = 3
    f3["time"] = 3.0
    f3["robots"] = [
        {"robot_id": 1, "position": (3, 4), "status": "MOVING", "battery": 95.0, "current_task_id": 101, "path": [(3, 4), (3, 5)]},
        {"robot_id": 2, "position": (6, 4), "status": "WAITING", "battery": 79.0, "current_task_id": 102, "path": [(6, 4), (7, 4)]},
        {"robot_id": 3, "position": (9, 4), "status": "MOVING", "battery": 88.0, "current_task_id": 103, "path": [(9, 4), (10, 4)]},
        {"robot_id": 4, "position": (1, 4), "status": "IDLE", "battery": 98.0, "current_task_id": None, "path": []},
    ]
    f3["conflicts"] = []
    steps.append(f3)

    # Frame 4: Delivery and completion
    f4 = dict(base)
    f4["timestep"] = 4
    f4["time"] = 4.0
    f4["robots"] = [
        {"robot_id": 1, "position": (3, 5), "status": "MOVING", "battery": 94.0, "current_task_id": 101, "path": [(3, 5), (4, 5)]},
        {"robot_id": 2, "position": (7, 4), "status": "MOVING", "battery": 78.0, "current_task_id": 102, "path": [(7, 4), (8, 4)]},
        {"robot_id": 3, "position": (10, 4), "status": "MOVING", "battery": 87.0, "current_task_id": 103, "path": []},
        {"robot_id": 4, "position": (1, 4), "status": "IDLE", "battery": 98.0, "current_task_id": None, "path": []},
    ]
    f4["conflicts"] = []
    steps.append(f4)

    return steps
