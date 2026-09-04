import math


class CollisionDetector:
    def distance(self, robot_a, robot_b):
        a, b = robot_a.state.position, robot_b.state.position
        return math.dist(a, b)
    def detect_collision(self, robot_a, robot_b, threshold=0.0): return self.distance(robot_a, robot_b) <= threshold
    def detect_all_collisions(self, robots, threshold=0.0):
        return [(a, b) for i, a in enumerate(robots) for b in robots[i + 1:] if self.detect_collision(a, b, threshold)]
    def detect_vertex_conflict(self, path_a, path_b): return any(a == b for a, b in zip(path_a, path_b))
    def detect_edge_conflict(self, path_a, path_b): return any(a == b_next and b == a_next for a, a_next, b, b_next in zip(path_a, path_a[1:], path_b, path_b[1:]))
    def predict_collision(self, robot_a, robot_b, horizon): return self.detect_vertex_conflict(robot_a.state.path[:horizon], robot_b.state.path[:horizon])
