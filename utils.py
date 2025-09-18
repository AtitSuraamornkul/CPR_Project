import random
import re
from robot import Robot

def create_group(group_id, count, grid_size, start_id=0):
    return [Robot(start_id + i, group_id, 
                  (random.randint(0, grid_size-1), random.randint(0, grid_size-1))) 
            for i in range(count)]

def strip_ansi(text):
    return re.sub(r'\x1b\[[0-9;]*m', '', text)
