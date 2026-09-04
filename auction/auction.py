from communication.message import Message, MessageType
from dataclasses import dataclass
from auction.task import TaskStatus


@dataclass
class AuctionResult:
    winner: object
    bids: list

    def __iter__(self): return iter((self.winner, self.bids))


class Auction:
    def __init__(self, network, robots, claim_timeout=0.3):
        self.network, self.robots, self.bids = network, list(robots), {}
        self.claim_timeout = claim_timeout
        self.rounds = {}
        self.claims = {}
        for robot in self.robots: robot.auction = self

    @staticmethod
    def task_payload(task, auction_id, round_number=0):
        return {"task_id": task.task_id, "pickup": tuple(task.pickup),
                "dropoff": tuple(task.dropoff), "priority": task.priority,
                "created_time": task.created_time, "deadline": task.deadline,
                "auction_id": auction_id, "round": round_number}

    def announce_task(self, task, auction_id=None):
        auction_id = auction_id or f"task-{task.task_id}-{task.created_time}"
        round_number = self.rounds.get(task.task_id, -1) + 1
        self.rounds[task.task_id] = round_number
        self.claims.pop(task.task_id, None)
        task.status = TaskStatus.AUCTIONING
        self.bids[task.task_id] = {}
        self.network.broadcast(-1, Message(-1, MessageType.TASK_AVAILABLE, task.created_time,
            self.task_payload(task, auction_id, round_number)))
        return auction_id, round_number

    def submit_bid(self, bid, auction_id=None, round_number=None):
        bids = self.bids.setdefault(bid.task_id, {})
        if isinstance(bids, list):
            bids = {("legacy", 0, item.robot_id): item for item in bids}
            self.bids[bid.task_id] = bids
        key = (auction_id, round_number, bid.robot_id)
        bids[key] = bid

    def collect_bids(self, task, auction_id=None, round_number=None):
        stored = self.bids.get(task.task_id, {})
        if not isinstance(stored, dict):
            return stored
        return [bid for (stored_auction, stored_round, _), bid in stored.items()
                if (auction_id is None or stored_auction == auction_id)
                and (round_number is None or stored_round == round_number)]

    def receive_bid(self, message):
        payload = message.payload
        bid = payload.get("bid")
        if isinstance(bid, dict):
            from auction.bid import Bid
            fields = {k: bid[k] for k in ("robot_id", "task_id", "travel_cost", "time_cost",
                "battery_cost", "congestion_cost", "priority_bonus", "timestamp", "valid") if k in bid}
            self.submit_bid(Bid(**fields), payload.get("auction_id"), payload.get("round"))

    def receive_claim(self, message):
        payload = message.payload
        self.claims[payload.get("task_id")] = (payload.get("robot_id"), payload.get("auction_id"), payload.get("round"))

    def release_task(self, task):
        """Return a failed task to the pending pool and notify all peers."""
        task.status = TaskStatus.PENDING
        task.assigned_robot_id = None
        self.bids.pop(task.task_id, None)
        self.announce_task(task)

    def select_winner(self, bids):
        ids = {r.robot_id for r in self.robots}
        valid = [b for b in bids if b.valid and b.robot_id in ids]
        return min(valid, key=lambda b: (b.total_cost, b.robot_id)) if valid else None

    def broadcast_winner(self, task, robot_id):
        task.assign(robot_id)
        robot = next((r for r in self.robots if r.robot_id == robot_id), None)
        if robot and task.task_id not in robot.tasks:
            robot.accept_task(task)
        self.network.broadcast(-1, Message(-1, MessageType.TASK_ASSIGNED, task.created_time, {"task_id": task.task_id, "robot_id": robot_id}))

    def run_auction(self, task, verbose=True):
        if not task.is_available(): return AuctionResult(None, self.bids.get(task.task_id, []))
        self.announce_task(task)
        bids = [r.calculate_bid(task) for r in self.robots if r.can_bid(task)]
        self.bids[task.task_id] = bids
        winner = self.select_winner(bids)
        if winner: self.broadcast_winner(task, winner.robot_id)
        if verbose:
            print(f"TASK {task.task_id + 1}")
            for bid in bids: print(bid.format())
            print(f"WINNER: R{winner.robot_id + 1}" if winner else "WINNER: NONE")
        return AuctionResult(winner, bids)

    def start_distributed(self, task):
        """Publish a task; robots calculate and resolve the winner themselves."""
        if not task.is_available():
            return None
        auction_id, round_number = self.announce_task(task)
        return auction_id, round_number
