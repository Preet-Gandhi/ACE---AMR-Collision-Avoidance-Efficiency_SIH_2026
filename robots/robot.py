from auction.bid import Bid
from communication.message import Message, MessageType
from robots.state import RobotState


class Robot:
    def __init__(self, robot_id, start_position, warehouse, planner, network, reservation_table, battery=100.0):
        self.robot_id, self.warehouse, self.planner = robot_id, warehouse, planner
        self.network, self.reservation_table = network, reservation_table
        self.state, self.known_states, self.tasks = RobotState(robot_id, tuple(start_position), battery=battery), {}, {}
        network.register(self)
        self.current_time = 0

    def can_bid(self, task): return task.is_available() and self.state.current_task_id is None
    def calculate_bid(self, task):
        path = self.planner.find_path(self.state.position, task.pickup)
        return Bid(self.robot_id, task.task_id, len(path) - 1 if path else float("inf"), battery_cost=max(0, len(path) - self.state.battery))
    def accept_task(self, task): self.tasks[task.task_id] = task; self.state.set_task(task.task_id); task.start()
    def plan_path(self):
        task = self.tasks[self.state.current_task_id]
        goal = task.dropoff if self.state.position == task.pickup else task.pickup
        path = self.planner.find_path(self.state.position, goal, self.reservation_table, self.current_time)
        if path and self.reservation_table.reserve_path(self.robot_id, path, self.current_time): self.state.set_path(path[1:])
        return path
    def broadcast_state(self):
        self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.STATE, 0, {"robot_id": self.robot_id, "position": self.state.position, "status": self.state.status}))
    def receive_message(self, message):
        if message.message_type == MessageType.STATE: self.known_states[message.sender_id] = message.payload
        elif message.message_type == MessageType.OBSTACLE:
            if self.state.current_task_id is not None: self.handle_blockage()
        elif message.message_type == MessageType.TASK_ASSIGNED and message.payload["robot_id"] == self.robot_id:
            task = self.warehouse.get_task(message.payload["task_id"])
            if task and task.task_id not in self.tasks: self.accept_task(task)
    def update(self):
        for message in self.network.receive(self.robot_id): self.receive_message(message)
        self.broadcast_state()
        if self.state.current_task_id is not None and self.state.get_next_position() is None: self.plan_path()

    def set_time(self, timestep): self.current_time = timestep
    def move(self):
        nxt = self.state.get_next_position()
        if nxt is None: return False
        self.state.update_velocity((nxt[0] - self.state.position[0], nxt[1] - self.state.position[1]))
        self.state.update_position(nxt); self.state.path_index += 1; self.state.consume_battery(1)
        return True
    def is_task_complete(self):
        task = self.tasks.get(self.state.current_task_id)
        return bool(task and self.state.position == task.dropoff and self.state.path_index >= len(self.state.path))
    def complete_task(self):
        task = self.tasks[self.state.current_task_id]; task.complete(); self.reservation_table.release(self.robot_id); self.state.clear_task(); self.state.clear_path()
    def handle_blockage(self): self.replan()
    def replan(self): self.reservation_table.release(self.robot_id); self.state.clear_path(); return self.plan_path()
    def request_reservation(self): return bool(self.state.path) and self.reservation_table.reserve_path(self.robot_id, self.state.path)
    def release_reservation(self): self.reservation_table.release(self.robot_id)
    def detect_conflict(self): return any(s.get("position") == self.state.get_next_position() for s in self.known_states.values())
    def handle_conflict(self): self.state.status = "WAITING"
