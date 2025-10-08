import numpy as np
import random

class Grid:
    def __init__(self, size=20, num_gold=10):
        self.size = size
        self.grid = np.zeros((size, size), dtype=int)
        self._place_deposits()
        self._place_gold(num_gold)
        self.num_gold = np.count_nonzero(self.grid == 1)

    def _place_deposits(self):
        # Fixed deposits: top-left for group 1, bottom-right for group 2
        self.grid[0, 0] = 2  # Group 1 deposit
        self.grid[self.size-1, self.size-1] = 3  # Group 2 deposit

    def _place_gold(self, num_gold):
        for _ in range(num_gold):
            x, y = random.randint(0, self.size-1), random.randint(0, self.size-1)
            if self.grid[x, y] == 0:  # Place gold only on empty cells
                self.grid[x, y] = 1

    def get_cell(self, pos):
        x, y = pos
        return self.grid[x, y]

    def update_cell(self, pos, value):
        x, y = pos
        self.grid[x, y] = value