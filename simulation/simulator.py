from planning.collision import CollisionDetector
from planning.deadlock import DeadlockDetector
from communication.message import Message, MessageType


class Simulator:
    def __init__(self, warehouse, robots, network, reservation_table, metrics, auction=None, dt=0.1):
        self.warehouse, self.robots, self.network = warehouse, list(robots), network
        self.reservation_table, self.metrics, self.auction = reservation_table, metrics, auction
        self.dt, self.time = dt, 0.0; self.collision_detector = CollisionDetector(); self.deadlock_detector = DeadlockDetector()
    def step(self):
        self.reservation_table.release_expired(round(self.time / self.dt))
        for robot in self.robots:
            robot.set_time(round(self.time / self.dt))
        for robot in sorted(self.robots, key=lambda item: (-item.calculate_priority(), item.robot_id)):
            robot.update()
        for robot in self.robots:
            if robot.detect_conflict(): robot.handle_conflict(self.dt)
            else:
                if robot.move(): self.metrics.record_movement(robot, 1.0)
        for a, b in self.collision_detector.detect_all_collisions(self.robots): self.metrics.record_collision(a, b)
        for a, b in self.collision_detector.detect_all_path_conflicts(self.robots):
            if (a, b) not in self.collision_detector.detect_all_collisions(self.robots):
                a.handle_conflict(self.dt); b.handle_conflict(self.dt)
        for robot in self.robots:
            if robot.is_task_complete():
                task = robot.tasks[robot.state.current_task_id]; robot.complete_task(); self.metrics.record_task_completed(task, robot)
        if self.deadlock_detector.detect_deadlocks(self.robots): self.metrics.record_deadlock(self.robots); self.deadlock_detector.resolve_deadlock(self.robots)
        self.time += self.dt
    def run(self, steps=1000):
        self.metrics.start_simulation(self.time)
        for _ in range(steps):
            if self.is_finished(): break
            self.step()
        self.metrics.end_simulation(self.time); return self.metrics.get_summary()
    def run_stop_and_wait(self, steps=1000):
        """Reference execution that advances only one robot per timestep."""
        self.metrics.start_simulation(self.time)
        for _ in range(steps):
            if self.is_finished(): break
            for robot in self.robots:
                robot.update()
                if robot.state.current_task_id is not None and robot.state.get_next_position() is None: robot.plan_path()
                if robot.move(): self.metrics.record_movement(robot, 1.0)
                if robot.is_task_complete():
                    task = robot.tasks[robot.state.current_task_id]; robot.complete_task(); self.metrics.record_task_completed(task, robot)
                self.time += self.dt
        self.metrics.end_simulation(self.time); return self.metrics.get_summary()
    def spawn_task(self, task): self.warehouse.add_task(task)
    def spawn_obstacle(self, position):
        self.warehouse.add_obstacle(position)
        for robot in self.robots:
            robot.network.broadcast(-1, Message(-1, MessageType.OBSTACLE, self.time, {"position": tuple(position)}))
    def remove_obstacle(self, position): self.warehouse.remove_obstacle(position)
    def is_finished(self): return all(t.status.value == "COMPLETED" for t in self.warehouse.tasks.values())
    def reset(self): self.time = 0.0; self.metrics.__init__(); self.reservation_table._reservations.clear()
