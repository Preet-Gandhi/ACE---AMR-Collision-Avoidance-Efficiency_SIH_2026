import heapq
from functools import lru_cache


class AStarPlanner:
    def __init__(self, warehouse):
        self.warehouse = warehouse

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, position):
        return self.warehouse.get_neighbors(position)

    @lru_cache(maxsize=4096)
    def static_distance(self, start, goal):
        start = tuple(start)
        goal = tuple(goal)
        if start == goal:
            return 0
        if not self.warehouse.is_walkable(start) or not self.warehouse.is_walkable(goal):
            return float("inf")
        frontier = [(0, start)]
        cost = {start: 0}
        while frontier:
            current_cost, current = heapq.heappop(frontier)
            if current == goal:
                return current_cost
            if current_cost != cost[current]:
                continue
            for neighbor in self.get_neighbors(current):
                neighbor = tuple(neighbor)
                if not self.warehouse.is_walkable(neighbor):
                    continue
                next_cost = current_cost + 1
                if next_cost < cost.get(neighbor, float("inf")):
                    cost[neighbor] = next_cost
                    heapq.heappush(frontier, (next_cost, neighbor))
        return float("inf")

    def find_path(
        self,
        start,
        goal,
        reservations=None,
        start_time=0,
        blocked=None,
        robot_id=None,
    ):
        """
        Find a shortest path using A*.

        blocked:
            Temporary cells that must not be used while planning.
            This is primarily used by deadlock recovery so that the
            selected robot does not immediately choose the same
            contested route again.
        """

        start = tuple(start)
        goal = tuple(goal)
        blocked = {tuple(position) for position in (blocked or [])}

        # The robot must be allowed to start from its current position.
        blocked.discard(start)

        if not self.warehouse.is_walkable(start):
            return []

        if not self.warehouse.is_walkable(goal):
            return []

        # If the goal itself is temporarily blocked, there is no
        # valid escape path.
        if goal in blocked and goal != start:
            return []

        frontier = []
        counter = 0

        # (f_score, counter, position)
        heapq.heappush(frontier, (0, counter, start))

        came_from = {}
        cost = {start: 0}

        while frontier:
            _, _, current = heapq.heappop(frontier)

            if current == goal:
                return self.reconstruct_path(came_from, current)

            for neighbor in self.get_neighbors(current):
                neighbor = tuple(neighbor)

                # Temporary deadlock-recovery block.
                if neighbor in blocked:
                    continue

                if not self.warehouse.is_walkable(neighbor):
                    continue

                next_cost = cost[current] + 1

                # Normal reservation check.
                if reservations is not None:
                    if reservations.is_reserved(
                        neighbor,
                        start_time + next_cost,
                    ):
                        if reservations.get_owner(neighbor, start_time + next_cost) != robot_id:
                            continue
                    edge_time = start_time + next_cost
                    edge_owner = reservations.get_edge_owner(current, neighbor, edge_time)
                    reverse_owner = reservations.get_edge_owner(neighbor, current, edge_time)
                    if edge_owner not in (None, robot_id) or reverse_owner not in (None, robot_id):
                        continue

                if next_cost < cost.get(
                    neighbor,
                    float("inf"),
                ):
                    cost[neighbor] = next_cost
                    came_from[neighbor] = current

                    counter += 1

                    priority = (
                        next_cost
                        + self.heuristic(neighbor, goal)
                    )

                    heapq.heappush(
                        frontier,
                        (
                            priority,
                            counter,
                            neighbor,
                        ),
                    )

        return []

    def reconstruct_path(self, came_from, current):
        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        return list(reversed(path))
