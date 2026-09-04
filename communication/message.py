from dataclasses import dataclass
from enum import Enum


class MessageType(str, Enum):
    STATE = "STATE"
    TASK_AVAILABLE = "TASK_AVAILABLE"
    BID = "BID"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    PATH_INTENT = "PATH_INTENT"
    RESERVATION_REQUEST = "RESERVATION_REQUEST"
    RESERVATION_GRANTED = "RESERVATION_GRANTED"
    RESERVATION_DENIED = "RESERVATION_DENIED"
    CONFLICT = "CONFLICT"
    DEADLOCK = "DEADLOCK"
    OBSTACLE = "OBSTACLE"
    TASK_COMPLETED = "TASK_COMPLETED"


@dataclass
class Message:
    sender_id: int
    message_type: MessageType
    timestamp: float
    payload: dict

    def to_dict(self):
        return {"sender_id": self.sender_id, "message_type": self.message_type.value, "timestamp": self.timestamp, "payload": self.payload}

    @classmethod
    def from_dict(cls, data):
        return cls(data["sender_id"], MessageType(data["message_type"]), data["timestamp"], data.get("payload", {}))
