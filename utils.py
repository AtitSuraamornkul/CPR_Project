import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any

def strip_ansi(text):
    """Remove ANSI escape codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class Direction(Enum):
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)

@dataclass
class PaxosMessage:
    """Message for Paxos consensus protocol"""
    msg_type: str  # 'prepare', 'promise', 'accept', 'accepted'
    proposal_id: int
    sender_id: int
    value: Optional[Any] = None
    accepted_id: Optional[int] = None
    accepted_value: Optional[Any] = None
