import time
from utils import strip_ansi

class Simulation:
    def __init__(self, grid, group1, group2, steps=500):
        self.grid = grid
        self.group1 = group1
        self.group2 = group2
        self.steps = steps
        self.scores = {1: 0, 2: 0}
        self.pickup_counts = {1: 0, 2: 0}

    def run(self):
        for step in range(self.steps):
            print(f"\nStep {step+1}")
            print("=" * 40)
            all_robots = self.group1 + self.group2

            # Process messages and handle world state changes like gold drops
            self._process_messages(all_robots)

            # Update all robots
            for robot in all_robots:
                robot.update(self.grid.grid, all_robots)

            # Process physical actions (gold pickup from grid)
            self._process_actions(all_robots)

            # Print grid view
            self._print_grid()
            
            # Print robot positions and scores
            positions = [(r.id, r.state, r.carrying_with, r.accepted_proposal) for r in all_robots]
            print(f"Robot states: {positions}")
            print(f"Scores - Group 1: {self.scores[1]}, Group 2: {self.scores[2]}")
            print(f"Pickups - Group 1: {self.pickup_counts[1]}, Group 2: {self.pickup_counts[2]}")

            if step < self.steps - 1:
                time.sleep(0.1)
        
        self._print_final_results()

    def _process_messages(self, all_robots):
        """
        Process all messages, and handle any direct world-state changes
        that result from them (e.g., dropping gold).
        """
        messages_to_deliver = []
        for robot in all_robots:
            messages_to_deliver.extend(robot.message_outbox)
            robot.message_outbox = []

        for msg in messages_to_deliver:
            # ** BUG FIX AREA **
            # Handle gold drop messages directly to update the grid
            if msg["type"] == "drop_gold":
                pos = tuple(msg["content"]["pos"])
                if self.grid.grid[pos] == 0: # Ensure gold is not already there
                    self.grid.grid[pos] = 1
                    print(f"DEBUG: Gold dropped back onto the grid at {pos}")

            # Deliver messages to recipients
            for robot in all_robots:
                if msg.get("broadcast"):
                    # The robot handles the drop_gold message to reset its own state
                    sender = next((r for r in all_robots if r.id == msg["sender_id"]), None)
                    if sender and robot.group == sender.group and robot.id != msg["sender_id"]:
                         robot.message_inbox.append(msg)

                elif "recipient_id" in msg and robot.id == msg["recipient_id"]:
                    robot.message_inbox.append(msg)


    def _process_actions(self, all_robots):
        """Handle physical world actions - gold pickup and deposits"""
        
        # Handle pickups
        for robot in all_robots:
            if robot.state == "carrying_gold" and robot.id < robot.carrying_with:
                partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
                if partner:
                    if robot.target_gold_pos and self.grid.grid[robot.target_gold_pos] > 0:
                        self.grid.grid[robot.target_gold_pos] -= 1
                        self.pickup_counts[robot.group] += 1
                        print(f"DEBUG: Pickup by Group {robot.group} at {robot.target_gold_pos}. Total pickups: {sum(self.pickup_counts.values())}")

        # Handle deposits
        for robot in all_robots:
            if robot.state == "at_deposit" and robot.holding_gold:
                deposit_pos = (0, 0) if robot.group == 1 else (self.grid.size-1, self.grid.size-1)
                if robot.position == deposit_pos:
                    partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
                    if partner and partner.holding_gold:
                        self.scores[robot.group] += 1
                        print(f"DEBUG: Score by Group {robot.group}, Robots {robot.id}&{partner.id}. Total score: {sum(self.scores.values())}")
                        
                        robot.holding_gold = False
                        partner.holding_gold = False
                        robot.state = "idle"
                        partner.state = "idle"
                        robot.carrying_with = None
                        partner.carrying_with = None


    def _print_grid(self):
        """Print a visual representation of the grid"""
        print("\nGrid View:")
        print("Legend: R1=Group1 (red), R2=Group2 (blue), *=carrying, ↑=N, ↓=S, →=E, ←=W, G=Gold, D1/D2=Deposit")
        print("-" * 50)
        
        display_grid = [["." for _ in range(self.grid.size)] for _ in range(self.grid.size)]
        
        RED = "\033[31m"
        BLUE = "\033[34m"
        YELLOW = "\033[33m"
        RESET = "\033[0m"
        
        display_grid[0][0] = 'D1'
        display_grid[self.grid.size-1][self.grid.size-1] = 'D2'
        
        for i in range(self.grid.size):
            for j in range(self.grid.size):
                if self.grid.grid[i, j] > 0 and (i, j) not in [(0, 0), (self.grid.size-1, self.grid.size-1)]:
                    display_grid[i][j] = f'{YELLOW}G{self.grid.grid[i, j]}{RESET}'
        
        all_robots = self.group1 + self.group2
        for robot in all_robots:
            x, y = robot.position
            direction_symbol = {'N': '↑', 'S': '↓', 'E': '→', 'W': '←'}[robot.direction]
            color = RED if robot.group == 1 else BLUE
            
            if robot.holding_gold:
                display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}*{RESET}'
            else:
                display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}{RESET}'
        
        header = '    ' + ''.join(f'{j:^7}' for j in range(self.grid.size))
        print(header)
        for i in range(self.grid.size):
            row_str = []
            for cell in display_grid[i]:
                visible_len = len(strip_ansi(cell))
                padding = ' ' * ((6 - visible_len) // 2)
                row_str.append(padding + cell + padding + (' ' if (6 - visible_len) % 2 != 0 else ''))
            print(f'{i:2d}: {" ".join(row_str)}')
        
        print('-' * (self.grid.size * 7))

    def _print_final_results(self):
        print(f"\nFINAL RESULTS:")
        print(f"Group 1 Score: {self.scores[1]}")
        print(f"Group 2 Score: {self.scores[2]}")
        print(f"Pickups - Group 1: {self.pickup_counts[1]}, Group 2: {self.pickup_counts[2]}")
        if self.scores[1] > self.scores[2]:
            print("Group 1 WINS!")
        elif self.scores[2] > self.scores[1]:
            print("Group 2 WINS!")
        else:
            print("It's a TIE!")