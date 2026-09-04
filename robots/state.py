from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RobotState:
    robot_id: int

    position: tuple[int, int]

    velocity: tuple[int, int] = (0, 0)

    battery: float = 100.0

    online: bool = True

    availability_state: str = "ONLINE"

    current_task_id: Optional[int] = None

    path: list[tuple[int, int]] = field(
        default_factory=list
    )

    path_index: int = 0

    status: str = "IDLE"

    carrying_package: bool = False

    def update_position(self, position):
        self.position = tuple(position)

    def update_velocity(self, velocity):
        self.velocity = tuple(velocity)

    def consume_battery(self, amount):
        self.battery = max(
            0.0,
            self.battery - amount,
        )

    def set_task(self, task_id):
        self.current_task_id = task_id
        self.status = "PLANNING"

    def clear_task(self):
        self.current_task_id = None
        if self.online:
            self.status = "IDLE"
        else:
            self.status = self.availability_state if self.availability_state != "ONLINE" else "OFFLINE"

    def set_path(self, path):
        self.path = list(path)
        self.path_index = 0

        if self.path:
            self.status = "MOVING"
        elif self.current_task_id is not None:
            self.status = "WAITING"

    def clear_path(self):
        self.path = []
        self.path_index = 0

    def get_next_position(self):
        if (
            self.path_index
            < len(self.path)
        ):
            return self.path[
                self.path_index
            ]

        return None
