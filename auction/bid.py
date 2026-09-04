from dataclasses import dataclass, field


@dataclass
class Bid:
    robot_id: int
    task_id: int
    travel_cost: float
    time_cost: float = 0.0
    battery_cost: float = 0.0
    congestion_cost: float = 0.0
    timestamp: float = 0.0
    total_cost: float = field(init=False)

    def __post_init__(self): self.calculate_total()
    def calculate_total(self):
        self.total_cost = self.travel_cost + self.time_cost + self.battery_cost + self.congestion_cost
        return self.total_cost
