class DeadlockDetector:
    def build_wait_graph(self, robots):
        graph = {r.robot_id: set() for r in robots}
        for robot in robots:
            owner = robot.reservation_table.get_owner(robot.state.get_next_position(), robot.state.path_index + 1) if robot.state.get_next_position() else None
            if owner is not None and owner != robot.robot_id: graph[robot.robot_id].add(owner)
        return graph
    def detect_cycle(self, graph):
        visiting, visited = set(), set()
        def visit(node):
            if node in visiting: return True
            if node in visited: return False
            visiting.add(node)
            if any(visit(n) for n in graph.get(node, ())): return True
            visiting.remove(node); visited.add(node); return False
        return any(visit(n) for n in graph)
    def detect_deadlocks(self, robots):
        graph = self.build_wait_graph(robots); return graph if self.detect_cycle(graph) else {}
    def select_robot_to_reroute(self, deadlocked_robots): return min(deadlocked_robots, key=lambda r: (r.state.battery, -r.state.path_index)) if deadlocked_robots else None
    def resolve_deadlock(self, robots):
        robot = self.select_robot_to_reroute(robots)
        if robot: robot.replan()
        return robot
