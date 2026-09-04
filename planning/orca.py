"""A small, dependency-free ORCA velocity solver.

The simulator currently moves robots between grid cells.  This module keeps
the ORCA calculation continuous, then lets the caller quantize the selected
velocity to a legal grid action.
"""

from dataclasses import dataclass
import math


Vector = tuple[float, float]


@dataclass(frozen=True)
class ORCAAgent:
    position: Vector
    velocity: Vector = (0.0, 0.0)
    preferred_velocity: Vector = (0.0, 0.0)
    radius: float = 0.5
    max_speed: float = 1.0


@dataclass(frozen=True)
class ORCALine:
    point: Vector
    direction: Vector


@dataclass(frozen=True)
class ORCAResult:
    velocity: Vector
    constraints: int
    feasible: bool
    used_fallback: bool = False


def _add(a: Vector, b: Vector) -> Vector:
    return a[0] + b[0], a[1] + b[1]


def _sub(a: Vector, b: Vector) -> Vector:
    return a[0] - b[0], a[1] - b[1]


def _mul(a: Vector, scalar: float) -> Vector:
    return a[0] * scalar, a[1] * scalar


def _dot(a: Vector, b: Vector) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _det(a: Vector, b: Vector) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _length(a: Vector) -> float:
    return math.hypot(a[0], a[1])


def _normalize(a: Vector, fallback: Vector = (1.0, 0.0)) -> Vector:
    length = _length(a)
    return _mul(a, 1.0 / length) if length > 1e-9 else fallback


def _clip_speed(velocity: Vector, max_speed: float) -> Vector:
    length = _length(velocity)
    if length <= max_speed or length <= 1e-9:
        return velocity
    return _mul(velocity, max_speed / length)


class ORCASolver:
    """Compute a velocity satisfying pairwise ORCA half-plane constraints."""

    def __init__(self, neighbor_distance=3.0, time_horizon=2.0, timestep=0.1):
        self.neighbor_distance = float(neighbor_distance)
        self.time_horizon = float(time_horizon)
        self.timestep = float(timestep)

    def nearby_agents(self, agent, neighbors):
        """Return agents that can affect ``agent`` within the neighbor radius."""
        result = []
        for neighbor in neighbors:
            if isinstance(neighbor, ORCAAgent):
                candidate = neighbor
            else:
                candidate = ORCAAgent(
                    tuple(neighbor.position),
                    tuple(getattr(neighbor, "velocity", (0.0, 0.0))),
                    tuple(getattr(neighbor, "preferred_velocity", (0.0, 0.0))),
                    float(getattr(neighbor, "radius", agent.radius)),
                    float(getattr(neighbor, "max_speed", agent.max_speed)),
                )
            if _length(_sub(candidate.position, agent.position)) <= self.neighbor_distance:
                result.append(candidate)
        return result

    def _line_for_neighbor(self, agent, neighbor):
        relative_position = _sub(neighbor.position, agent.position)
        relative_velocity = _sub(agent.velocity, neighbor.velocity)
        combined_radius = max(0.0, agent.radius + neighbor.radius)
        distance = _length(relative_position)
        if distance <= 1e-9:
            relative_position = (1.0, 0.0)
            distance = 1.0

        # The construction follows the standard velocity-obstacle ORCA
        # tangent construction.  The resulting line keeps velocity on its
        # left side, which is the feasible side of the constraint.
        inv_horizon = 1.0 / max(self.time_horizon, self.timestep, 1e-6)
        radius_sq = combined_radius * combined_radius
        distance_sq = distance * distance
        w = _sub(relative_velocity, _mul(relative_position, inv_horizon))
        w_length = _length(w)
        dot_product = _dot(w, relative_position)

        if distance_sq > radius_sq and dot_product < 0.0 and dot_product * dot_product > radius_sq * _dot(w, w):
            unit_w = _normalize(w)
            u = _mul(unit_w, combined_radius * inv_horizon - w_length)
            direction = (unit_w[1], -unit_w[0])
        else:
            if distance > combined_radius:
                leg = math.sqrt(max(0.0, distance_sq - radius_sq))
                if _det(relative_position, w) > 0.0:
                    direction = ((relative_position[0] * leg - relative_position[1] * combined_radius) / distance_sq,
                                 (relative_position[0] * combined_radius + relative_position[1] * leg) / distance_sq)
                else:
                    direction = ((-relative_position[0] * leg - relative_position[1] * combined_radius) / distance_sq,
                                 (relative_position[0] * combined_radius - relative_position[1] * leg) / distance_sq)
                direction = _normalize(direction)
                projection = _dot(relative_velocity, direction)
                u = _sub(_mul(direction, projection), relative_velocity)
            else:
                inv_step = 1.0 / max(self.timestep, 1e-6)
                unit_position = _normalize(relative_position)
                u = _mul(unit_position, (combined_radius - distance) * inv_step - _dot(relative_velocity, unit_position))
                direction = (unit_position[1], -unit_position[0])

        point = _add(agent.velocity, _mul(u, 0.5))
        return ORCALine(point, _normalize(direction))

    @staticmethod
    def _satisfies(line, velocity, epsilon=1e-7):
        # ORCA lines use the standard convention that the feasible side is
        # the left side when looking from the candidate velocity toward the
        # line direction.
        return _det(line.direction, _sub(line.point, velocity)) >= -epsilon

    def constraints(self, agent, neighbors):
        return [self._line_for_neighbor(agent, other) for other in self.nearby_agents(agent, neighbors)]

    def _candidates(self, agent, lines):
        preferred = _clip_speed(agent.preferred_velocity, agent.max_speed)
        candidates = [preferred, (0.0, 0.0)]
        speed = max(0.0, agent.max_speed)
        candidates.extend((math.cos(angle) * speed, math.sin(angle) * speed) for angle in (
            0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4,
            math.pi, 5 * math.pi / 4, 3 * math.pi / 2, 7 * math.pi / 4,
        ))

        for line in lines:
            projection = _add(line.point, _mul(line.direction, _dot(_sub(preferred, line.point), line.direction)))
            candidates.append(_clip_speed(projection, speed))

        for first in range(len(lines)):
            for second in range(first + 1, len(lines)):
                determinant = _det(lines[first].direction, lines[second].direction)
                if abs(determinant) <= 1e-9:
                    continue
                offset = _sub(lines[second].point, lines[first].point)
                scale = _det(offset, lines[second].direction) / determinant
                candidates.append(_clip_speed(_add(lines[first].point, _mul(lines[first].direction, scale)), speed))
        return candidates

    def compute_velocity(self, agent, neighbors):
        lines = self.constraints(agent, neighbors)
        preferred = _clip_speed(agent.preferred_velocity, agent.max_speed)
        feasible = [candidate for candidate in self._candidates(agent, lines)
                    if _length(candidate) <= agent.max_speed + 1e-7
                    and all(self._satisfies(line, candidate) for line in lines)]
        if feasible:
            selected = min(feasible, key=lambda value: _length(_sub(value, preferred)))
            return ORCAResult(selected, len(lines), True, False)
        return ORCAResult((0.0, 0.0), len(lines), False, True)
