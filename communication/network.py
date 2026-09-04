from collections import defaultdict, deque


class Network:
    def __init__(self): self.peers, self.queues = {}, defaultdict(deque)
    def register(self, robot): self.peers[robot.robot_id] = robot
    def unregister(self, robot_id): self.peers.pop(robot_id, None); self.queues.pop(robot_id, None)
    def send(self, sender_id, receiver_id, message):
        if receiver_id in self.peers: self.queues[receiver_id].append(message)
    def broadcast(self, sender_id, message):
        for robot_id in self.peers:
            if robot_id != sender_id: self.send(sender_id, robot_id, message)
    def receive(self, robot_id):
        messages = list(self.queues[robot_id]); self.queues[robot_id].clear(); return messages
    def get_connected_robots(self, robot_id):
        return [
            peer_id
            for peer_id, robot in self.peers.items()
            if peer_id != robot_id and robot.is_online()
        ]
    def get_all_robots(self, robot_id=None):
        return [peer_id for peer_id in self.peers if peer_id != robot_id]
