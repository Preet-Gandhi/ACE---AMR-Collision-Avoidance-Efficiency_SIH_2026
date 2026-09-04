from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    grid_width: int = 30
    grid_height: int = 20
    num_robots: int = 3
    simulation_dt: float = 0.1
    robot_speed: float = 1.0
    initial_battery: float = 100.0
    reservation_horizon: int = 20
    deadlock_timeout: float = 5.0
    collision_distance: float = 0.0
    auction_interval: float = 1.0
    random_seed: int = 42
    robot_speed: float = 1.0
    congestion_penalty: float = 2.0
    priority_bonus: float = 1.0
    invalid_bid_penalty: float = 1_000_000.0
