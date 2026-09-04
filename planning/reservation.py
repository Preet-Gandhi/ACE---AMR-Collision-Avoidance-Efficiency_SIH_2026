from dataclasses import dataclass


@dataclass(frozen=True)
class Reservation:
    robot_id: int
    position: tuple[int, int]
    timestep: int


class ReservationTable:
    def __init__(self):
        self._reservations = {}
        self._priorities = {}
    def reserve(self, robot_id, position, timestep):
        key = (tuple(position), timestep)
        if key in self._reservations and self._reservations[key] != robot_id: return False
        self._reservations[key] = robot_id; return True
    def release(self, robot_id): self._reservations = {k: v for k, v in self._reservations.items() if v != robot_id}
    def is_reserved(self, position, timestep): return (tuple(position), timestep) in self._reservations
    def get_owner(self, position, timestep): return self._reservations.get((tuple(position), timestep))
    def get_robot_reservations(self, robot_id): return [Reservation(robot_id, p, t) for (p, t), owner in self._reservations.items() if owner == robot_id]
    def get_reservations_at(self, timestep):
        return {position: owner for (position, time), owner in self._reservations.items() if time == timestep}

    def register_priority(self, robot_id, priority): self._priorities[robot_id] = priority

    def release_expired(self, timestep):
        self._reservations = {key: owner for key, owner in self._reservations.items() if key[1] >= timestep}

    def path_conflicts(self, robot_id, path, start_time=0):
        conflicts = []
        for index, position in enumerate(path):
            timestep = start_time + index
            owner = self.get_owner(position, timestep)
            if owner is not None and owner != robot_id:
                conflicts.append(("vertex", tuple(position), timestep, owner))
            if index:
                previous = tuple(path[index - 1])
                current = tuple(position)
                previous_owner = self.get_owner(current, timestep - 1)
                current_owner = self.get_owner(previous, timestep)
                if previous_owner is not None and previous_owner != robot_id and current_owner == previous_owner:
                    conflicts.append(("edge", previous, current, timestep, previous_owner))
        return conflicts

    def first_conflict(self, robot_id, path, start_time=0):
        conflicts = self.path_conflicts(robot_id, path, start_time)
        return conflicts[0] if conflicts else None

    def count_conflicts(self, path, robot_id=None):
        return len(self.path_conflicts(robot_id, path))
    def can_reserve(self, robot_id, path, start_time=0): return not self.path_conflicts(robot_id, path, start_time)
    def reserve_path(self, robot_id, path, start_time=0, priority=None):
        if priority is not None: self.register_priority(robot_id, priority)
        conflicts = self.path_conflicts(robot_id, path, start_time)
        if conflicts:
            blocking_ids = {conflict[-1] for conflict in conflicts}
            requester_priority = self._priorities.get(robot_id, 0)
            blocking_priority = max(self._priorities.get(owner, 0) for owner in blocking_ids)
            if requester_priority <= blocking_priority: return False
            for owner in blocking_ids: self.release(owner)
            if not self.can_reserve(robot_id, path, start_time): return False
        return all(self.reserve(robot_id, p, start_time + i) for i, p in enumerate(path))
