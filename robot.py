import random
from actions import get_turn_direction

class Robot:
    def __init__(self, rid, group, pos, direction=None):
        self.id = rid
        self.group = group
        self.position = pos
        self.direction = direction if direction else random.choice(['N','S','E','W'])
        self.holding_gold = False
        self.carrying_with = None  # ID of robot carrying gold together
        self.history = []
        self.action = None
        self.gold_sensed = False
        self.path = []
        self.waiting_for_partner = False
        self.waiting_timer = 0
        self.message_inbox = []

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

    def decide_action(self, grid):
        # If holding gold, go to the deposit
        if self.holding_gold:
            self.waiting_for_partner = False
            self.waiting_timer = 0
            deposit_pos = (0, 0) if self.group == 1 else (grid.size-1, grid.size-1)
            path = []
            dx = deposit_pos[0] - self.position[0]
            dy = deposit_pos[1] - self.position[1]

            if dx > 0: path.extend(['S'] * dx)
            if dx < 0: path.extend(['N'] * -dx)
            if dy > 0: path.extend(['E'] * dy)
            if dy < 0: path.extend(['W'] * -dy)
            self.path = path
        else:
            # Process messages (placeholder for now)
            if self.message_inbox:
                print(f"Robot {self.id} received messages: {self.message_inbox}")
                self.message_inbox = [] # Clear inbox after processing

            # Sensing for gold
            sensed_data = self.sense(grid.size, grid.grid)
            gold_pos = None
            if any(d[2] == 1 for d in sensed_data):
                self.gold_sensed = True
                gold_pos = next(d for d in sensed_data if d[2] == 1)
                # Simple pathfinding: move towards gold
                path = []
                dx = gold_pos[0] - self.position[0]
                dy = gold_pos[1] - self.position[1]
                if dx > 0: path.extend(['S'] * dx)
                if dx < 0: path.extend(['N'] * -dx)
                if dy > 0: path.extend(['E'] * dy)
                if dy < 0: path.extend(['W'] * -dy)
                self.path = path
            else:
                self.gold_sensed = False
                self.path = []

        on_gold = grid.grid[self.position] == 1

        if self.waiting_for_partner:
            if self.waiting_timer > 15:
                self.waiting_for_partner = False
                self.waiting_timer = 0
                self.action = random.choice(['move', 'turn_left', 'turn_right'])
            else:
                self.waiting_timer += 1
                self.action = 'pick_up'
        elif on_gold and not self.holding_gold:
            self.action = 'pick_up'
            self.waiting_for_partner = True
        elif self.path:
            # Follow the path
            next_move = self.path[0]
            if self.direction != next_move:
                turn_action = get_turn_direction(self.direction, next_move)
                if turn_action:
                    self.action = turn_action
                else:
                    self.action = 'move' # Should not happen if logic is correct
                    self.path.pop(0)
            else:
                self.action = 'move'
                self.path.pop(0)
        else:
            # Random action if no gold is sensed or path is complete
            self.action = random.choice(['move', 'turn_left', 'turn_right'])