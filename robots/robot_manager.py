class RobotManager:
    def __init__(self): self.robots = {}
    def add_robot(self, robot): self.robots[robot.robot_id] = robot
    def remove_robot(self, robot_id): return self.robots.pop(robot_id, None)
    def get_robot(self, robot_id): return self.robots.get(robot_id)
    def get_all_robots(self): return list(self.robots.values())
    def get_robot_states(self): return [r.state for r in self.robots.values()]
    def update_all(self):
        for robot in self.robots.values(): robot.update()
    def get_active_robots(self): return [r for r in self.robots.values() if r.state.status not in ("IDLE", "COMPLETED")]
