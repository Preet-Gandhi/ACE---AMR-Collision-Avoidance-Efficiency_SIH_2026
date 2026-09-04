from auction.bid import Bid
from communication.message import Message, MessageType
from planning.orca import ORCAAgent, ORCASolver
from robots.state import RobotState


class Robot:
    def __init__(self, robot_id, start_position, warehouse, planner, network, reservation_table, battery=100.0, robot_speed=1.0, congestion_penalty=2.0, priority_bonus=1.0, invalid_bid_penalty=1_000_000.0, orca_enabled=False, orca_neighbor_distance=3.0, orca_time_horizon=2.0, orca_robot_radius=0.5, orca_max_speed=1.0):
        self.robot_id, self.warehouse, self.planner = robot_id, warehouse, planner
        self.network, self.reservation_table = network, reservation_table
        self.state, self.known_states, self.tasks = RobotState(robot_id, tuple(start_position), battery=battery), {}, {}
        self.task_queue = []
        self.initial_battery = battery
        self.waiting_time = 0.0
        self.distance_travelled = 0.0
        self.last_priority = 0.0
        self.wait_threshold = 5.0
        self.blockage_waiting = 0.0
        self.auction = None
        self.robot_speed, self.congestion_penalty, self.priority_bonus, self.invalid_bid_penalty = robot_speed, congestion_penalty, priority_bonus, invalid_bid_penalty
        self.orca_enabled = orca_enabled
        self.orca_robot_radius = orca_robot_radius
        self.orca_max_speed = orca_max_speed
        self.orca_solver = ORCASolver(orca_neighbor_distance, orca_time_horizon, 0.1)
        self._orca_target = None
        self._orca_result = None
        self._orca_preferred_velocity = (0.0, 0.0)
        network.register(self)
        self.current_time = 0
        reservation_table.register_priority(robot_id, 0)

    def can_bid(self, task): return task.is_available() and task.task_id not in self.tasks and task.task_id not in {t.task_id for t in self.task_queue}

    def _projected_position(self):
        if self.task_queue: return self.task_queue[-1].dropoff
        if self.state.current_task_id is not None: return self.tasks[self.state.current_task_id].dropoff
        return self.state.position

    def calculate_bid(self, task):
        projected = self._projected_position()
        to_pickup = self.planner.find_path(projected, task.pickup)
        to_dropoff = self.planner.find_path(task.pickup, task.dropoff)
        if not to_pickup or not to_dropoff:
            return Bid(self.robot_id, task.task_id, self.invalid_bid_penalty, valid=False)
        route = to_pickup + to_dropoff[1:]
        distance = len(route) - 1
        time_cost = distance / self.robot_speed if self.robot_speed > 0 else self.invalid_bid_penalty
        congestion = self.reservation_table.count_conflicts(route, self.robot_id) * self.congestion_penalty
        projected_battery = self.state.battery - distance
        battery_cost = 0.0 if projected_battery >= 0 else self.invalid_bid_penalty
        valid = projected_battery >= 0 and self.robot_speed > 0
        return Bid(self.robot_id, task.task_id, distance, time_cost, battery_cost, congestion, task.priority * self.priority_bonus, valid=valid)

    def accept_task(self, task):
        if task.task_id in self.tasks or task.task_id in {t.task_id for t in self.task_queue}: return False
        if task.assigned_robot_id != self.robot_id: raise ValueError("task is assigned to another robot")
        self.tasks[task.task_id] = task
        if self.state.current_task_id is None:
            self.state.set_task(task.task_id); task.start()
        else:
            self.task_queue.append(task)
        return True
    def plan_path(self):
        task = self.tasks[self.state.current_task_id]
        goal = task.dropoff if self.state.position == task.pickup else task.pickup
        path = self.planner.find_path(self.state.position, goal, self.reservation_table, self.current_time)
        priority = self.calculate_priority()
        self.last_priority = priority
        if path and self.reservation_table.reserve_path(self.robot_id, path, self.current_time, priority):
            self.state.set_path(path[1:])
        elif path:
            self.state.clear_path(); self.state.status = "WAITING"
        return path

    def is_path_valid(self):
        remaining = self.state.path[self.state.path_index:]
        return all(self.warehouse.is_walkable(position) for position in remaining)

    def handle_obstacle(self, position, announce=True):
        if self.state.current_task_id is None: return False
        if announce:
            self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.OBSTACLE_DETECTED, self.current_time, {"position": tuple(position)}))
        if tuple(position) not in self.state.path[self.state.path_index:]: return True
        self.release_reservation()
        self.state.clear_path()
        self.blockage_waiting = 0.0
        if self.plan_path(): return True
        self.state.status = "WAITING"
        return False

    def fail_current_task(self):
        if self.state.current_task_id is None: return None
        task = self.tasks.pop(self.state.current_task_id)
        task.cancel()
        self.release_reservation()
        self.state.clear_path()
        self.state.clear_task()
        if self.auction is not None: self.auction.release_task(task)
        return task
    def broadcast_state(self):
        self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.STATE, self.current_time, {"robot_id": self.robot_id, "position": self.state.position, "velocity": self.state.velocity, "status": self.state.status}))
    def receive_message(self, message):
        if message.message_type == MessageType.STATE: self.known_states[message.sender_id] = message.payload
        elif message.message_type in (MessageType.OBSTACLE, MessageType.OBSTACLE_DETECTED):
            self.handle_obstacle(message.payload.get("position"), announce=False)
        elif message.message_type == MessageType.TASK_ASSIGNED and message.payload["robot_id"] == self.robot_id:
            task = self.warehouse.get_task(message.payload["task_id"])
            if task and task.task_id not in self.tasks: self.accept_task(task)
    def update(self):
        for message in self.network.receive(self.robot_id): self.receive_message(message)
        self.broadcast_state()
        if self.state.current_task_id is not None and self.state.get_next_position() is None:
            if not self.plan_path():
                self.blockage_waiting += 0.1
                if self.blockage_waiting >= self.wait_threshold: self.fail_current_task()

    def set_time(self, timestep): self.current_time = timestep
    def prepare_orca(self, robots, duration=0.1):
        """Choose a local grid target using ORCA without changing the A* path."""
        self._orca_target = None
        self._orca_result = None
        self._orca_preferred_velocity = (0.0, 0.0)
        if not self.orca_enabled:
            return None
        nxt = self.state.get_next_position()
        if nxt is None:
            return None
        dx, dy = nxt[0] - self.state.position[0], nxt[1] - self.state.position[1]
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= 1e-9:
            return None
        preferred = (dx / distance * self.orca_max_speed, dy / distance * self.orca_max_speed)
        self.orca_solver.timestep = max(duration, 1e-6)
        agent = ORCAAgent(tuple(map(float, self.state.position)), tuple(map(float, self.state.velocity)), preferred, self.orca_robot_radius, self.orca_max_speed)
        others = []
        for other in robots:
            if other.robot_id == self.robot_id:
                continue
            others.append(ORCAAgent(tuple(map(float, other.state.position)), tuple(map(float, other.state.velocity)), (0.0, 0.0), self.orca_robot_radius, self.orca_max_speed))
        result = self.orca_solver.compute_velocity(agent, others)
        self._orca_result = result
        self._orca_preferred_velocity = preferred

        if result.feasible and (result.velocity[0] ** 2 + result.velocity[1] ** 2) > 1e-8:
            # In the discrete phase ORCA is advisory: the A* waypoint stays
            # authoritative. Arbitrary side-steps belong to the future
            # continuous movement phase because they invalidate reservations.
            if not any(nxt == other.state.position or
                       getattr(other, "_orca_target", None) == self.state.position
                       for other in robots if other.robot_id != self.robot_id):
                owner = self.reservation_table.get_owner(nxt, self.current_time + 1)
                if owner in (None, self.robot_id):
                    if owner is None:
                        self.reservation_table.reserve(self.robot_id, nxt, self.current_time + 1)
                    self._orca_target = nxt
        elif result.used_fallback:
            # Reservation ownership is the discrete safety authority. If the
            # continuous constraint approximation has no sampled velocity,
            # retain the already-reserved A* step instead of starving a task.
            if not any(nxt == other.state.position or
                       getattr(other, "_orca_target", None) == self.state.position
                       for other in robots if other.robot_id != self.robot_id):
                if self.reservation_table.get_owner(nxt, self.current_time + 1) == self.robot_id:
                    self._orca_target = nxt
        return result

    def move(self):
        planned = self.state.get_next_position()
        nxt = self._orca_target if self.orca_enabled and self._orca_result is not None else planned
        detour = nxt is not None and planned is not None and nxt != planned
        self._orca_target = None
        if nxt is None: return False
        if not self.warehouse.is_walkable(nxt):
            return False
        if self.reservation_table.get_owner(nxt, self.current_time + 1) != self.robot_id:
            self.state.status = "WAITING"
            self.waiting_time += 0.1
            self.blockage_waiting += 0.1
            if self.waiting_time >= self.wait_threshold:
                self.replan()
            if self.blockage_waiting >= self.wait_threshold and not self.is_path_valid():
                self.fail_current_task()
            return False
        self.state.update_velocity((nxt[0] - self.state.position[0], nxt[1] - self.state.position[1]))
        self.state.update_position(nxt)
        if planned == nxt:
            self.state.path_index += 1
        self.state.consume_battery(1)
        self.distance_travelled += 1.0
        self.waiting_time = 0.0
        self.blockage_waiting = 0.0
        if detour:
            # A grid side-step changes the route's adjacency. Rebuild the
            # remaining route from the new cell on the next planning state.
            self.release_reservation()
            self.state.clear_path()
            self.plan_path()
        return True
    def is_task_complete(self):
        task = self.tasks.get(self.state.current_task_id)
        return bool(task and self.state.position == task.dropoff and self.state.path_index >= len(self.state.path))
    def complete_task(self):
        task = self.tasks[self.state.current_task_id]; task.complete(); self.reservation_table.release(self.robot_id); self.state.clear_path()
        if self.task_queue:
            next_task = self.task_queue.pop(0)
            self.state.set_task(next_task.task_id); next_task.start()
        else:
            self.state.clear_task()
    def handle_blockage(self): self.replan()
    def replan(self): self.reservation_table.release(self.robot_id); self.state.clear_path(); return self.plan_path()
    def request_reservation(self): return bool(self.state.path) and self.reservation_table.reserve_path(self.robot_id, self.state.path)
    def release_reservation(self): self.reservation_table.release(self.robot_id)
    def detect_conflict(self):
        next_position = self._orca_target if self.orca_enabled and self._orca_result is not None else self.state.get_next_position()
        return next_position is not None and self.reservation_table.get_owner(next_position, self.current_time + 1) not in (None, self.robot_id)
    def calculate_priority(self):
        task_priority = 0
        if self.state.current_task_id is not None:
            task_priority = self.tasks[self.state.current_task_id].priority
        battery_urgency = (self.initial_battery - self.state.battery) / self.initial_battery if self.initial_battery else 1.0
        self.last_priority = task_priority + self.waiting_time + self.distance_travelled * 0.1 + battery_urgency
        return self.last_priority

    def handle_conflict(self, duration=0.1):
        self.state.status = "WAITING"
        self.waiting_time += duration
