from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    AUCTIONING = "AUCTIONING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Task:
    task_id: int
    pickup: tuple[int, int]
    dropoff: tuple[int, int]
    priority: int = 0
    created_time: float = 0.0
    deadline: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    assigned_robot_id: Optional[int] = None

    def assign(self, robot_id: int) -> None:
        if not self.is_available():
            raise ValueError("task is not available")
        self.assigned_robot_id = robot_id
        self.status = TaskStatus.ASSIGNED

    def start(self) -> None:
        if self.status not in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS):
            raise ValueError("task must be assigned before starting")
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED

    def cancel(self) -> None:
        self.status = TaskStatus.FAILED

    def is_available(self) -> bool:
        return self.status in (TaskStatus.PENDING, TaskStatus.AUCTIONING)
