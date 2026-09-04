from communication.message import Message, MessageType
from dataclasses import dataclass


@dataclass
class AuctionResult:
    winner: object
    bids: list

    def __iter__(self): return iter((self.winner, self.bids))


class Auction:
    def __init__(self, network, robots):
        self.network, self.robots, self.bids = network, list(robots), {}
        for robot in self.robots: robot.auction = self

    def announce_task(self, task):
        task.status = "AUCTIONING"
        self.network.broadcast(-1, Message(-1, MessageType.TASK_AVAILABLE, task.created_time, {"task_id": task.task_id}))

    def submit_bid(self, bid): self.bids.setdefault(bid.task_id, []).append(bid)
    def collect_bids(self, task): return self.bids.get(task.task_id, [])

    def release_task(self, task):
        """Return a failed task to the pending pool and notify all peers."""
        task.status = "PENDING"
        task.assigned_robot_id = None
        self.bids.pop(task.task_id, None)
        self.network.broadcast(-1, Message(-1, MessageType.TASK_AVAILABLE, task.created_time, {"task_id": task.task_id}))

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
