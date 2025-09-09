import random
from robot import Robot

def create_group(group_id, count, grid_size):
    return [Robot(i, group_id, 
                  (random.randint(0, grid_size-1), random.randint(0, grid_size-1))) 
            for i in range(count)]
