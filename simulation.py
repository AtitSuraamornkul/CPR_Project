import random
import time
from actions import move, turn, pick_up, move_with_gold, check_deposit_delivery, get_turn_direction
from utils import strip_ansi

class Simulation:
    def __init__(self, grid, group1, group2, steps=50):
        self.grid = grid
        self.group1 = group1
        self.group2 = group2
        self.steps = steps
        self.scores = {1: 0, 2: 0}  # Track scores for each group
        self.pickup_counts = {1: 0, 2: 0}

    def run(self):
        for step in range(self.steps):
            print(f"\nStep {step+1}")
            print("=" * 40)
            all_robots = self.group1 + self.group2

            # Determine actions for all robots first
            for robot in all_robots:
                # Sensing for gold
                sensed_data = robot.sense(self.grid.size, self.grid.grid)
                gold_pos = None
                if any(d[2] == 1 for d in sensed_data):
                    robot.gold_sensed = True
                    gold_pos = next(d for d in sensed_data if d[2] == 1)
                    # Simple pathfinding: move towards gold
                    path = []
                    dx = gold_pos[0] - robot.position[0]
                    dy = gold_pos[1] - robot.position[1]
                    if dx > 0: path.extend(['S'] * dx)
                    if dx < 0: path.extend(['N'] * -dx)
                    if dy > 0: path.extend(['E'] * dy)
                    if dy < 0: path.extend(['W'] * -dy)
                    robot.path = path
                else:
                    robot.gold_sensed = False
                    robot.path = []

                if robot.path:
                    # Follow the path
                    next_move = robot.path[0]
                    if robot.direction != next_move:
                        turn_action = get_turn_direction(robot.direction, next_move)
                        if turn_action:
                            robot.action = turn_action
                        else:
                            robot.action = 'move' # Should not happen if logic is correct
                            robot.path.pop(0)
                    else:
                        robot.action = 'move'
                        robot.path.pop(0)
                elif robot.gold_sensed and gold_pos and robot.position == gold_pos[:2]:
                    robot.action = 'pick_up'
                    robot.waiting_for_partner = True
                elif robot.waiting_for_partner:
                    robot.action = 'pick_up'
                else:
                    # Random action if no gold is sensed or path is complete
                    robot.action = random.choice(['move', 'turn_left', 'turn_right'])

            # Execute actions
            for robot in all_robots:
                if robot.action == 'pick_up':
                    # The pick_up logic will be handled in a centralized way to avoid redundant calls
                    pass
                else:
                    if robot.action == 'move':
                        if robot.holding_gold:
                            move_with_gold(robot, self.grid.size, all_robots)
                        else:
                            move(robot, self.grid.size)
                    elif robot.action == 'turn_left':
                        turn(robot, 'left')
                    elif robot.action == 'turn_right':
                        turn(robot, 'right')

            # Process pickups for all positions with gold
            for x in range(self.grid.size):
                for y in range(self.grid.size):
                    if self.grid.grid[x, y] > 0:
                        robots_here = [r for r in all_robots if r.position == (x, y) and r.action == 'pick_up']
                        if robots_here:
                            pick_up(robots_here, self.grid.grid)


            # Print grid view
            self._print_grid()
            
            # Print robot positions and scores
            positions = [(r.id, r.group, r.position, r.direction, r.holding_gold, r.carrying_with) for r in all_robots]
            print(f"Robot positions: {positions}")
            print(f"Scores - Group 1: {self.scores[1]}, Group 2: {self.scores[2]}")
            print(f"Pickups - Group 1: {self.pickup_counts[1]}, Group 2: {self.pickup_counts[2]}")
            
            # Add delay between steps (except for the last step)
            if step < self.steps - 1:
                time.sleep(1)
        
        # Print final results
        print(f"\n🏁 FINAL RESULTS:")
        print(f"Group 1 Score: {self.scores[1]}")
        print(f"Group 2 Score: {self.scores[2]}")
        print(f"Pickups - Group 1: {self.pickup_counts[1]}, Group 2: {self.pickup_counts[2]}")
        if self.scores[1] > self.scores[2]:
            print("Group 1 WINS!")
        elif self.scores[2] > self.scores[1]:
            print("Group 2 WINS!")
        else:
            print("It's a TIE!")
    
    def _print_grid(self):
        """Print a visual representation of the grid"""
        print("\nGrid View:")
        print("Legend: R1=Group1 (red), R2=Group2 (blue), * carrying pair, ! carrying alone, ↑=North, ↓=South, →=East, ←=West, G=Gold (yellow), D1=Group1 Deposit, D2=Group2 Deposit")
        print("-" * 50)
        
        # Create a display grid
        display_grid = [['.' for _ in range(self.grid.size)] for _ in range(self.grid.size)]
        
        # ANSI colors
        RED = "\033[31m"
        BLUE = "\033[34m"
        YELLOW = "\033[33m"
        RESET = "\033[0m"
        
        # Mark deposits
        display_grid[0][0] = 'D1'  # Group 1 deposit
        display_grid[self.grid.size-1][self.grid.size-1] = 'D2'  # Group 2 deposit
        
        # Mark gold
        for i in range(self.grid.size):
            for j in range(self.grid.size):
                if self.grid.grid[i, j] > 0 and (i, j) not in [(0, 0), (self.grid.size-1, self.grid.size-1)]:
                    display_grid[i][j] = f'{YELLOW}G{self.grid.grid[i, j]}{RESET}'
        
        # Mark robots
        all_robots = self.group1 + self.group2
        for robot in all_robots:
            x, y = robot.position
            # Map symbols: ↑=North, ↓=South, →=East, ←=West
            direction_symbol = {'N': '↑', 'S': '↓', 'E': '→', 'W': '←'}[robot.direction]
            color = RED if robot.group == 1 else BLUE
            
            if robot.holding_gold:
                if robot.carrying_with:
                    display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}*{RESET}'  # * indicates holding gold with partner
                else:
                    display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}!{RESET}'  # ! indicates holding gold alone (will drop)
            elif robot.waiting_for_partner:
                display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}!{RESET}' # ! indicates waiting for partner
            elif robot.gold_sensed:
                display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}#{RESET}' # # indicates gold sensed
            else:
                display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}{RESET}'
        
        # Print the grid
        # Print column (Y) indices header
        header = '    ' + ''.join(f'{j:^7}' for j in range(self.grid.size))
        print(header)
        for i in range(self.grid.size):
            row_str = []
            for cell in display_grid[i]:
                visible_len = len(strip_ansi(cell))
                padding = ' ' * ((6 - visible_len) // 2)
                row_str.append(padding + cell + padding + (' ' if (6 - visible_len) % 2 != 0 else ''))
            print(f"{i:2d}: {' '.join(row_str)}")
        
        print("-" * (self.grid.size * 7))
