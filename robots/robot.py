from auction.bid import Bid
from auction.task import Task
from communication.message import Message, MessageType
from planning.orca import ORCAAgent, ORCASolver
from robots.state import RobotState


class Robot:
    def __init__(self, robot_id, start_position, warehouse, planner, network, reservation_table, battery=100.0, robot_speed=1.0, congestion_penalty=2.0, priority_bonus=1.0, invalid_bid_penalty=1_000_000.0, orca_enabled=False, orca_neighbor_distance=3.0, orca_time_horizon=2.0, orca_robot_radius=0.5, orca_max_speed=1.0, distributed=False, reservation_lease=20):
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
        self.replan_count = 0
        self.auction = None
        self.distributed = distributed
        self.reservation_lease = reservation_lease
        self.auction_rounds = {}
        self.auction_bids = {}
        self.auction_bid_rounds = {}
        self.claimed_auctions = set()
        self.pending_claims = {}
        self.plan_version = 0
        self.reservation_leases = {}
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
    def _choose_available_dropoff(self, task):
        """Move a delivery to another bay slot if its assigned slot is occupied."""
        if not self.state.carrying_package:
            return
        cells = list(getattr(self.warehouse, "dropoff_cells", ()))
        if not cells:
            return
        occupied = {tuple(self.state.position)}
        for payload in self.known_states.values():
            position = payload.get("position") if isinstance(payload, dict) else None
            if position is not None:
                occupied.add(tuple(position))
        if tuple(task.dropoff) not in occupied:
            return
        free = [cell for cell in cells if tuple(cell) not in occupied and self.warehouse.is_walkable(cell)]
        if free:
            task.dropoff = min(free, key=lambda cell: (abs(cell[0] - self.state.position[0]) + abs(cell[1] - self.state.position[1]), cell))

    def plan_path(self):
        task = self.tasks[self.state.current_task_id]
        # Reaching the pickup cell completes the pickup phase.
        if not self.state.carrying_package and self.state.position == task.pickup:
            self.state.carrying_package = True
        self._choose_available_dropoff(task)
        goal = task.dropoff if self.state.carrying_package else task.pickup
        path = self.planner.find_path(self.state.position, goal, self.reservation_table, self.current_time)
        priority = self.calculate_priority()
        self.last_priority = priority
        if path and self.distributed:
            self._request_reservation(path, priority)
        reservable = path and self.reservation_table.can_reserve(self.robot_id, path, self.current_time)
        if reservable and self.reservation_table.reserve_path(self.robot_id, path, self.current_time, priority):
            self.state.set_path(path[1:])
            self.plan_version += 1
            if self.distributed:
                self._broadcast_reservation(MessageType.RESERVATION_GRANTED, path, priority)
        elif path:
            self.state.clear_path(); self.state.status = "WAITING"
            if self.distributed:
                self._broadcast_reservation(MessageType.RESERVATION_DENIED, path, priority)
        return path

    def _broadcast_reservation(self, message_type, path, priority):
        payload = {"robot_id": self.robot_id, "path": [tuple(p) for p in path],
                   "start_time": int(self.current_time), "priority": priority,
                   "plan_version": self.plan_version, "lease_until": int(self.current_time) + self.reservation_lease}
        self.network.broadcast(self.robot_id, Message(self.robot_id, message_type, self.current_time, payload))

    def _request_reservation(self, path, priority):
        self._broadcast_reservation(MessageType.RESERVATION_REQUEST, path, priority)

    def _bid_payload(self, bid, auction_id, round_number):
        return {"auction_id": auction_id, "round": round_number,
                "bid": {"robot_id": bid.robot_id, "task_id": bid.task_id,
                         "travel_cost": bid.travel_cost, "time_cost": bid.time_cost,
                         "battery_cost": bid.battery_cost, "congestion_cost": bid.congestion_cost,
                         "priority_bonus": bid.priority_bonus, "timestamp": bid.timestamp,
                         "valid": bid.valid}}

    def _make_task_from_payload(self, payload):
        task = self.warehouse.get_task(payload["task_id"])
        if task is None:
            task = Task(payload["task_id"], tuple(payload["pickup"]), tuple(payload["dropoff"]),
                        payload.get("priority", 0), payload.get("created_time", 0.0), payload.get("deadline"))
            self.warehouse.add_task(task)
        return task

    def _handle_task_available(self, payload):
        task = self._make_task_from_payload(payload)
        auction_id = payload.get("auction_id", f"task-{task.task_id}")
        round_number = int(payload.get("round", 0))
        if round_number < self.auction_rounds.get(task.task_id, -1) or not task.is_available():
            return
        if round_number > self.auction_rounds.get(task.task_id, -1):
            self.auction_bids[task.task_id] = {}
            self.auction_bid_rounds[task.task_id] = {}
            self.claimed_auctions.discard(task.task_id)
        self.auction_rounds[task.task_id] = round_number
        bid = self.calculate_bid(task) if self.can_bid(task) else Bid(
            self.robot_id, task.task_id, self.invalid_bid_penalty, valid=False)
        self.auction_bids.setdefault(task.task_id, {})[self.robot_id] = bid
        self.auction_bid_rounds.setdefault(task.task_id, {})[self.robot_id] = round_number
        if self.auction is not None:
            self.auction.submit_bid(bid, auction_id, round_number)
        self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.BID, self.current_time,
            self._bid_payload(bid, auction_id, round_number) | {"task_id": task.task_id}))
        self._resolve_distributed_auction(dict(payload, task_id=task.task_id))

    def _resolve_distributed_auction(self, payload):
        task_id = payload.get("task_id")
        task = self.warehouse.get_task(task_id)
        if task is None or not task.is_available():
            return
        round_number = int(payload.get("round", self.auction_rounds.get(task_id, 0)))
        current_round = self.auction_rounds.get(task_id, round_number)
        if self.auction is not None:
            bids = list(self.auction.collect_bids(task, payload.get("auction_id"), current_round))
        else:
            bids = [bid for robot_id, bid in self.auction_bids.get(task_id, {}).items()
                    if self.auction_bid_rounds.get(task_id, {}).get(robot_id) == current_round]
        peers = len(self.network.get_connected_robots(self.robot_id)) + 1
        if len({bid.robot_id for bid in bids}) < peers:
            return
        valid = [bid for bid in bids if bid.valid and bid.robot_id in set(self.network.peers)]
        winner = min(valid, key=lambda bid: (bid.total_cost, bid.robot_id)) if valid else None
        if winner is None or task_id in self.claimed_auctions:
            return
        self.claimed_auctions.add(task_id)
        claim = {"task_id": task_id, "robot_id": winner.robot_id,
                 "auction_id": payload.get("auction_id"), "round": round_number}
        if self.auction is not None:
            self.auction.claims[task_id] = (winner.robot_id, claim["auction_id"], round_number)
        claim_timeout = getattr(self.auction, "claim_timeout", 0.3)
        deadline = self.current_time if not self.network.get_connected_robots(self.robot_id) else self.current_time + claim_timeout
        self.pending_claims[task_id] = (winner.robot_id, round_number, deadline)
        if winner.robot_id == self.robot_id:
            self.state.status = "WAITING"
        self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.AUCTION_CLAIM, self.current_time, claim))
        self._commit_pending_claims()

    def _commit_pending_claims(self):
        for task_id, (winner_id, round_number, deadline) in list(self.pending_claims.items()):
            if self.current_time < deadline:
                continue
            task = self.warehouse.get_task(task_id)
            if task and task.is_available() and winner_id == self.robot_id:
                task.assign(self.robot_id)
                self.accept_task(task)
            self.pending_claims.pop(task_id, None)

    def _handle_reservation_message(self, message):
        payload = message.payload
        owner = payload.get("robot_id", message.sender_id)
        path = [tuple(p) for p in payload.get("path", [])]
        version = int(payload.get("plan_version", 0))
        if version < self.reservation_leases.get(owner, {}).get("plan_version", -1):
            return
        self.reservation_leases[owner] = {"plan_version": version, "lease_until": payload.get("lease_until", 0)}
        if message.message_type == MessageType.RESERVATION_GRANTED and path:
            self.reservation_table.register_priority(owner, payload.get("priority", 0))
            self.reservation_table.reserve_path(owner, path, payload.get("start_time", self.current_time), payload.get("priority", 0))
        elif message.message_type in (MessageType.RESERVATION_RELEASED, MessageType.RESERVATION_PREEMPTED):
            self.reservation_table.release(owner)

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
        self.state.carrying_package = False
        self.release_reservation()
        self.state.clear_path()
        self.state.clear_task()
        if self.auction is not None: self.auction.release_task(task)
        return task
    def broadcast_state(self):
        self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.STATE, self.current_time, {"robot_id": self.robot_id, "position": self.state.position, "velocity": self.state.velocity, "status": self.state.status}))
    def receive_message(self, message):
        if message.message_type == MessageType.STATE: self.known_states[message.sender_id] = message.payload
        elif message.message_type == MessageType.TASK_AVAILABLE and self.distributed:
            self._handle_task_available(message.payload)
        elif message.message_type == MessageType.BID and self.distributed:
            payload = message.payload
            bid_data = payload.get("bid", {})
            if bid_data:
                fields = {k: bid_data[k] for k in ("robot_id", "task_id", "travel_cost", "time_cost",
                    "battery_cost", "congestion_cost", "priority_bonus", "timestamp", "valid") if k in bid_data}
                bid = Bid(**fields)
                bid_round = int(payload.get("round", 0))
                if bid_round < self.auction_rounds.get(bid.task_id, -1):
                    return
                self.auction_bids.setdefault(bid.task_id, {})[bid.robot_id] = bid
                self.auction_bid_rounds.setdefault(bid.task_id, {})[bid.robot_id] = bid_round
                if self.auction is not None: self.auction.receive_bid(message)
            self._resolve_distributed_auction(message.payload)
        elif message.message_type == MessageType.AUCTION_CLAIM and self.distributed:
            if self.auction is not None: self.auction.receive_claim(message)
            task = self.warehouse.get_task(message.payload.get("task_id"))
            if task and task.is_available():
                self.pending_claims[task.task_id] = (
                    message.payload.get("robot_id"), int(message.payload.get("round", 0)),
                    self.current_time + getattr(self.auction, "claim_timeout", 0.3))
        elif message.message_type == MessageType.RESERVATION_REQUEST:
            payload = message.payload
            path = [tuple(p) for p in payload.get("path", [])]
            owner = payload.get("robot_id", message.sender_id)
            priority = payload.get("priority", 0)
            allowed = bool(path) and self.reservation_table.can_reserve(
                owner, path, payload.get("start_time", self.current_time))
            response_type = MessageType.RESERVATION_GRANTED if allowed else MessageType.RESERVATION_DENIED
            self.network.send(self.robot_id, message.sender_id, Message(message.sender_id, response_type,
                self.current_time, dict(payload, responder_id=self.robot_id)))
        elif message.message_type in (MessageType.RESERVATION_GRANTED, MessageType.RESERVATION_DENIED,
                                      MessageType.RESERVATION_RELEASED, MessageType.RESERVATION_PREEMPTED):
            self._handle_reservation_message(message)
        elif message.message_type in (MessageType.OBSTACLE, MessageType.OBSTACLE_DETECTED):
            self.handle_obstacle(message.payload.get("position"), announce=False)
        elif message.message_type == MessageType.TASK_ASSIGNED and message.payload["robot_id"] == self.robot_id:
            task = self.warehouse.get_task(message.payload["task_id"])
            if task and task.task_id not in self.tasks: self.accept_task(task)
    def update(self):
        for message in self.network.receive(self.robot_id): self.receive_message(message)
        if self.distributed:
            self._commit_pending_claims()
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

    def move(self, blocked_positions=None):
        planned = self.state.get_next_position()
        nxt = self._orca_target if self.orca_enabled and self._orca_result is not None else planned
        detour = nxt is not None and planned is not None and nxt != planned
        self._orca_target = None
        if nxt is None: return False
        if not self.warehouse.is_walkable(nxt):
            return False
        # Physical occupancy is an independent safety layer. A reservation
        # bug must never allow a robot to drive into another robot.
        blocked_positions = {tuple(p) for p in (blocked_positions or [])}
        if tuple(nxt) in blocked_positions:
            self.state.status = "WAITING"
            self.waiting_time += 0.1
            self.blockage_waiting += 0.1
            return False
        reservation_time = int(self.current_time) + 1
        owner = self.reservation_table.get_owner(nxt, reservation_time)
        if owner not in (None, self.robot_id):
            self.state.status = "WAITING"
            self.waiting_time += 0.1
            self.blockage_waiting += 0.1
            if self.waiting_time >= self.wait_threshold:
                self.replan()
            if self.blockage_waiting >= self.wait_threshold and not self.is_path_valid():
                self.fail_current_task()
            return False
        # A path reservation can expire while the robot is waiting. If the
        # cell is physically free, claim the next vertex and edge for this
        # actual tick instead of freezing until the old reservation timeline
        # catches up.
        if owner is None:
            previous = tuple(self.state.position)
            if not self.reservation_table.reserve(self.robot_id, nxt, reservation_time):
                self.state.status = "WAITING"
                self.waiting_time += 0.1
                return False
            if not self.reservation_table.reserve_edge(self.robot_id, previous, tuple(nxt), reservation_time):
                self.reservation_table.release(self.robot_id)
                self.state.status = "WAITING"
                self.waiting_time += 0.1
                return False
        self.state.update_velocity((nxt[0] - self.state.position[0], nxt[1] - self.state.position[1]))
        self.state.update_position(nxt)
        task = self.tasks.get(self.state.current_task_id) if self.state.current_task_id is not None else None
        if task is not None and self.state.position == task.pickup:
            self.state.carrying_package = True
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
        task = self.tasks[self.state.current_task_id]
        task.complete()
        self.reservation_table.release(self.robot_id)
        self.state.carrying_package = False
        self.state.clear_path()
        if self.task_queue:
            next_task = self.task_queue.pop(0)
            self.state.set_task(next_task.task_id); next_task.start()
        else:
            self.state.clear_task()
    def handle_blockage(self): self.replan()
    def replan(self):
        self.replan_count += 1
        self.reservation_table.release(self.robot_id)
        self.state.clear_path()
        return self.plan_path()
    def request_reservation(self): return bool(self.state.path) and self.reservation_table.reserve_path(self.robot_id, self.state.path)
    def release_reservation(self):
        self.reservation_table.release(self.robot_id)
        if self.distributed:
            self.network.broadcast(self.robot_id, Message(self.robot_id, MessageType.RESERVATION_RELEASED,
                self.current_time, {"robot_id": self.robot_id, "plan_version": self.plan_version,
                                     "lease_until": int(self.current_time)}))
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

