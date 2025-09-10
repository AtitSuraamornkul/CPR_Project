import random

class Robot:
    def __init__(self, rid, group, pos, direction=None):
        self.id = rid
        self.group = group
        self.position = pos
        self.direction = direction if direction else random.choice(['N','S','E','W'])
        self.holding_gold = False
        self.carrying_with = None  # ID of robot carrying gold together
        self.history = []

    def sense(self, grid_size, grid):
        x, y = self.position
        positions = []

        if self.direction == 'N':
            positions = [(x-1,y-1),(x-1,y),(x-1,y+1),
                         (x-2,y-2),(x-2,y-1),(x-2,y),(x-2,y+1),(x-2,y+2)]
        elif self.direction == 'S':
            positions = [(x+1,y-1),(x+1,y),(x+1,y+1),
                         (x+2,y-2),(x+2,y-1),(x+2,y),(x+2,y+1),(x+2,y+2)]
        elif self.direction == 'E':
            positions = [(x-1,y+1),(x,y+1),(x+1,y+1),
                         (x-2,y+2),(x-1,y+2),(x,y+2),(x+1,y+2),(x+2,y+2)]
        elif self.direction == 'W':
            positions = [(x-1,y-1),(x,y-1),(x+1,y-1),
                         (x-2,y-2),(x-1,y-2),(x,y-2),(x+1,y-2),(x+2,y-2)]

        # Filter out-of-bounds
        valid = [(i,j) for i,j in positions if 0 <= i < grid_size and 0 <= j < grid_size]
        return [(i,j,grid[i,j]) for i,j in valid]
