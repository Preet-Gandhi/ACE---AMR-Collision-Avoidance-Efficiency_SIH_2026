from dataclasses import dataclass


@dataclass(frozen=True)
class Reservation:
    robot_id: int
    position: tuple[int, int]
    timestep: int


class ReservationTable:
    """Time-expanded vertex + directed-edge reservation table."""

    def __init__(self):
        self._reservations = {}
        self._edge_reservations = {}
        self._priorities = {}

    @staticmethod
    def _pos(position):
        return tuple(position)

    def reserve(self, robot_id, position, timestep):
        key = (self._pos(position), int(timestep))
        owner = self._reservations.get(key)

        if owner is not None and owner != robot_id:
            return False

        self._reservations[key] = robot_id
        return True

    def reserve_edge(self, robot_id, source, target, timestep):
        source = self._pos(source)
        target = self._pos(target)
        timestep = int(timestep)

        key = (source, target, timestep)
        reverse = (target, source, timestep)

        owner = self._edge_reservations.get(key)
        reverse_owner = self._edge_reservations.get(reverse)

        if owner is not None and owner != robot_id:
            return False

        if reverse_owner is not None and reverse_owner != robot_id:
            return False

        self._edge_reservations[key] = robot_id
        return True

    def release(self, robot_id):
        self._reservations = {
            k: v for k, v in self._reservations.items()
            if v != robot_id
        }

        self._edge_reservations = {
            k: v for k, v in self._edge_reservations.items()
            if v != robot_id
        }

    def is_reserved(self, position, timestep):
        return (
            self._pos(position),
            int(timestep),
        ) in self._reservations

    def get_owner(self, position, timestep):
        return self._reservations.get(
            (self._pos(position), int(timestep))
        )

    def get_edge_owner(self, source, target, timestep):
        return self._edge_reservations.get(
            (
                self._pos(source),
                self._pos(target),
                int(timestep),
            )
        )

    def get_robot_reservations(self, robot_id):
        return [
            Reservation(robot_id, position, timestep)
            for (position, timestep), owner
            in self._reservations.items()
            if owner == robot_id
        ]

    def get_reservations_at(self, timestep):
        timestep = int(timestep)

        return {
            position: owner
            for (position, time), owner
            in self._reservations.items()
            if time == timestep
        }

    def register_priority(self, robot_id, priority):
        self._priorities[robot_id] = priority

    def release_expired(self, timestep):
        timestep = int(timestep)

        self._reservations = {
            key: owner
            for key, owner in self._reservations.items()
            if key[1] >= timestep
        }

        self._edge_reservations = {
            key: owner
            for key, owner in self._edge_reservations.items()
            if key[2] >= timestep
        }

    def path_conflicts(self, robot_id, path, start_time=0):
        conflicts = []

        path = [
            self._pos(position)
            for position in path
        ]

        start_time = int(start_time)

        for index, position in enumerate(path):
            timestep = start_time + index

            owner = self.get_owner(
                position,
                timestep,
            )

            if owner is not None and owner != robot_id:
                conflicts.append(
                    (
                        "vertex",
                        position,
                        timestep,
                        owner,
                    )
                )

            if index > 0:
                previous = path[index - 1]
                current = position

                # Forward edge.
                edge_owner = self.get_edge_owner(
                    previous,
                    current,
                    timestep,
                )

                if edge_owner is not None and edge_owner != robot_id:
                    conflicts.append(
                        (
                            "edge",
                            previous,
                            current,
                            timestep,
                            edge_owner,
                        )
                    )

                # Reverse edge = head-on collision.
                reverse_owner = self.get_edge_owner(
                    current,
                    previous,
                    timestep,
                )

                if reverse_owner is not None and reverse_owner != robot_id:
                    conflicts.append(
                        (
                            "edge",
                            previous,
                            current,
                            timestep,
                            reverse_owner,
                        )
                    )

        return conflicts

    def first_conflict(self, robot_id, path, start_time=0):
        conflicts = self.path_conflicts(
            robot_id,
            path,
            start_time,
        )

        return conflicts[0] if conflicts else None

    def count_conflicts(self, path, robot_id=None):
        return len(
            self.path_conflicts(
                robot_id,
                path,
            )
        )

    def can_reserve(self, robot_id, path, start_time=0):
        return not self.path_conflicts(
            robot_id,
            path,
            start_time,
        )

    def reserve_path(
        self,
        robot_id,
        path,
        start_time=0,
        priority=None,
    ):
        path = [
            self._pos(position)
            for position in path
        ]

        if not path:
            return False

        start_time = int(start_time)

        if priority is not None:
            self.register_priority(
                robot_id,
                priority,
            )

        conflicts = self.path_conflicts(
            robot_id,
            path,
            start_time,
        )

        if conflicts:
            blocking_ids = {
                conflict[-1]
                for conflict in conflicts
            }

            requester_priority = self._priorities.get(
                robot_id,
                0,
            )

            blocking_priority = max(
                (
                    self._priorities.get(
                        owner,
                        0,
                    )
                    for owner in blocking_ids
                ),
                default=0,
            )

            if requester_priority <= blocking_priority:
                return False

            for owner in blocking_ids:
                self.release(owner)

            if not self.can_reserve(
                robot_id,
                path,
                start_time,
            ):
                return False

        added_vertices = []
        added_edges = []

        for index, position in enumerate(path):
            timestep = start_time + index

            if not self.reserve(
                robot_id,
                position,
                timestep,
            ):
                self._rollback(
                    robot_id,
                    added_vertices,
                    added_edges,
                )
                return False

            added_vertices.append(
                (
                    position,
                    timestep,
                )
            )

            if index > 0:
                source = path[index - 1]
                target = path[index]

                if not self.reserve_edge(
                    robot_id,
                    source,
                    target,
                    timestep,
                ):
                    self._rollback(
                        robot_id,
                        added_vertices,
                        added_edges,
                    )
                    return False

                added_edges.append(
                    (
                        source,
                        target,
                        timestep,
                    )
                )

        return True

    def _rollback(
        self,
        robot_id,
        vertices,
        edges,
    ):
        for key in vertices:
            if self._reservations.get(key) == robot_id:
                del self._reservations[key]

        for key in edges:
            if self._edge_reservations.get(key) == robot_id:
                del self._edge_reservations[key]