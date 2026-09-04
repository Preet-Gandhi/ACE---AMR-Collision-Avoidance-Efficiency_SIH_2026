import heapq


class AStarPlanner:
    def __init__(self, warehouse): self.warehouse = warehouse
    def heuristic(self, a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
    def get_neighbors(self, position): return self.warehouse.get_neighbors(position)

    def find_path(self, start, goal, reservations=None, start_time=0):
        if not self.warehouse.is_walkable(start) or not self.warehouse.is_walkable(goal): return []
        frontier, came_from, cost = [(0, 0, start)], {}, {start: 0}
        counter = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current == goal: return self.reconstruct_path(came_from, current)
            for neighbor in self.get_neighbors(current):
                next_cost = cost[current] + 1
                if reservations and reservations.is_reserved(neighbor, start_time + next_cost): continue
                if next_cost < cost.get(neighbor, float("inf")):
                    cost[neighbor], came_from[neighbor] = next_cost, current
                    counter += 1
                    heapq.heappush(frontier, (next_cost + self.heuristic(neighbor, goal), counter, neighbor))
        return []

    def reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return list(reversed(path))
