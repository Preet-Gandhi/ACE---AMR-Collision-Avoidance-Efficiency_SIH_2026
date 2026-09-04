from dataclasses import dataclass, field


@dataclass
class Bid:
    robot_id: int
    task_id: int
    travel_cost: float
    time_cost: float = 0.0
    battery_cost: float = 0.0
    congestion_cost: float = 0.0
    priority_bonus: float = 0.0
    timestamp: float = 0.0
    total_cost: float = field(init=False)
    valid: bool = True

    def __post_init__(self): self.calculate_total()
    def calculate_total(self):
        self.total_cost = self.travel_cost + self.time_cost + self.battery_cost + self.congestion_cost - self.priority_bonus
        return self.total_cost

    def format(self, display_robot_id=None):
        label = display_robot_id if display_robot_id is not None else self.robot_id + 1
        return f"R{label} bid: {self.total_cost:.1f}"
