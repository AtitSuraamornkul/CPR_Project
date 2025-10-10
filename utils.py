import re
from enum import Enum

def strip_ansi(text):
    """Remove ANSI escape codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|[\[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class Direction(Enum):
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)

