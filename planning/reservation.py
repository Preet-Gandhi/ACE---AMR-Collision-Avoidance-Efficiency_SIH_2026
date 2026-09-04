from dataclasses import dataclass


@dataclass(frozen=True)
class Reservation:
    robot_id: int
    position: tuple[int, int]
    timestep: int


class ReservationTable:
    def __init__(self): self._reservations = {}
    def reserve(self, robot_id, position, timestep):
        key = (tuple(position), timestep)
        if key in self._reservations and self._reservations[key] != robot_id: return False
        self._reservations[key] = robot_id; return True
    def release(self, robot_id): self._reservations = {k: v for k, v in self._reservations.items() if v != robot_id}
    def is_reserved(self, position, timestep): return (tuple(position), timestep) in self._reservations
    def get_owner(self, position, timestep): return self._reservations.get((tuple(position), timestep))
    def get_robot_reservations(self, robot_id): return [Reservation(robot_id, p, t) for (p, t), owner in self._reservations.items() if owner == robot_id]
    def can_reserve(self, robot_id, path, start_time=0): return all(self.get_owner(p, start_time + i) in (None, robot_id) for i, p in enumerate(path))
    def reserve_path(self, robot_id, path, start_time=0):
        if not self.can_reserve(robot_id, path, start_time): return False
        return all(self.reserve(robot_id, p, start_time + i) for i, p in enumerate(path))
