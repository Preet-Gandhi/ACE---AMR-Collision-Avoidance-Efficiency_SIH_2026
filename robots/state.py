from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RobotState:
    robot_id: int
    position: tuple[int, int]
    velocity: tuple[int, int] = (0, 0)
    battery: float = 100.0
    current_task_id: Optional[int] = None
    path: list[tuple[int, int]] = field(default_factory=list)
    path_index: int = 0
    status: str = "IDLE"

    def update_position(self, position): self.position = tuple(position)
    def update_velocity(self, velocity): self.velocity = tuple(velocity)
    def consume_battery(self, amount): self.battery = max(0.0, self.battery - amount)
    def set_task(self, task_id): self.current_task_id, self.status = task_id, "PLANNING"
    def clear_task(self): self.current_task_id, self.status = None, "IDLE"
    def set_path(self, path):
        self.path, self.path_index = list(path), 0
        self.status = "MOVING" if self.path else "WAITING"
    def clear_path(self): self.path, self.path_index = [], 0
    def get_next_position(self):
        return self.path[self.path_index] if self.path_index < len(self.path) else None
