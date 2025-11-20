"""
Simulation class for running the robot gold collection game
"""
import random
from collections import defaultdict

from utils import strip_ansi


class Simulation:
    def __init__(self, grid, group1, group2, steps=500, message_delay_range=(1, 5)):
        self.grid = grid
        self.group1 = group1
        self.group2 = group2
        self.steps = steps
        self.scores = {1: 0, 2: 0}
        self.pickup_counts = {1: 0, 2: 0}
        
        # Message delay system
        self.message_delay_range = message_delay_range  # (min_delay, max_delay) in steps
        self.delayed_messages = []  # List of (delivery_step, message) tuples
        self.current_step = 0

    def run(self):
        step = 0
        while step < self.steps:
            self.current_step = step
            print(f"\nStep {step+1}")
            print("=" * 40)
            all_robots = self.group1 + self.group2

            self._process_delayed_messages(all_robots)
            self._process_messages(all_robots)

            for robot in all_robots:
                # Strict Mode: Calculate visible cells outside the robot
                visible_cells = {}
                
                # 1. Vision (Front cone)
                for pos in robot.get_visible_positions():
                    visible_cells[pos] = self.grid.get_cell(pos)
                
                # 2. Proprioception/Touch (Current position)
                # Robot needs to know if it is standing on gold
                visible_cells[robot.position] = self.grid.get_cell(robot.position)
                
                robot.update(visible_cells)

            self._execute_actions(all_robots)

            self._print_grid()
            
            states = []
            for r in all_robots:
                states.append(f"R{r.id}@{r.position}: {r.state}, role={r.role}, partner={r.carrying_with}, gold={r.holding_gold}, target={r.target_gold_pos}")
            print(f"Robot details:")
            for s in states:
                print(f"  {s}")
            print(f"Scores - Group 1: {self.scores[1]}, Group 2: {self.scores[2]}")
            print(f"Pickups - Group 1: {self.pickup_counts[1]}, Group 2: {self.pickup_counts[2]}")
            print(f"Pending delayed messages: {len(self.delayed_messages)}")

            # Check for end condition
            if self.scores[1] + self.scores[2] >= self.grid.num_gold:
                print("\nAll gold has been deposited! Ending simulation.")
                break

            #if step < self.steps - 1:
             #  time.sleep(0.05)
            
            step += 1
        
        self._print_final_results()

    def _process_delayed_messages(self, all_robots):
        """Deliver messages that have reached their delivery time"""
        messages_to_deliver = []
        remaining_messages = []
        
        for delivery_step, msg in self.delayed_messages:
            if delivery_step <= self.current_step:
                messages_to_deliver.append(msg)
            else:
                remaining_messages.append((delivery_step, msg))
        
        self.delayed_messages = remaining_messages
        
        # Deliver messages that are ready
        for msg in messages_to_deliver:
            for robot in all_robots:
                if msg.get("broadcast"):
                    sender = next((r for r in all_robots if r.id == msg["sender_id"]), None)
                    if sender and robot.group == sender.group and robot.id != msg["sender_id"]:
                        robot.message_inbox.append(msg)
                elif "recipient_id" in msg and robot.id == msg["recipient_id"]:
                    robot.message_inbox.append(msg)
        
        if messages_to_deliver:
            print(f"DEBUG: Delivered {len(messages_to_deliver)} delayed messages at step {self.current_step}")
    
    def _process_messages(self, all_robots):
        """Collect outgoing messages and add delays"""
        messages_to_send = []
        for robot in all_robots:
            messages_to_send.extend(robot.message_outbox)
            robot.message_outbox = []

        for msg in messages_to_send:
            # Handle gold drop messages immediately (no delay for physical actions)
            if msg["type"] == "drop_gold":
                pos = tuple(msg["content"]["pos"])
                if self.grid.grid[pos] == 0:
                    self.grid.grid[pos] = 1
                    print(f"DEBUG: Gold dropped at {pos}")
            else:
                # Add random delay to message delivery
                delay = random.randint(self.message_delay_range[0], self.message_delay_range[1])
                delivery_step = self.current_step + delay
                self.delayed_messages.append((delivery_step, msg))
                
                # Optional: print debug info for finder-helper messages to see delays
                if msg["type"] in ["found", "response", "ack", "here", "ack2"]:
                    print(f"DEBUG: {msg['type']} from R{msg['sender_id']} scheduled for step {delivery_step} (delay: {delay})")

    def _execute_actions(self, all_robots):
        """Execute robot actions and handle game mechanics"""
        
        # Group pickup attempts by position
        pickup_attempts = defaultdict(lambda: defaultdict(list))
        actions = {}
        
        for robot in all_robots:
            action = robot.next_action
            actions[robot.id] = action
            
            if action == "pickup" and not robot.holding_gold:
                pickup_attempts[robot.position][robot.group].append(robot)
        
        # Process pickups
        for pos, groups in pickup_attempts.items():
            for group, robots_at_pos in groups.items():
                if len(robots_at_pos) == 2:
                    gold_available = self.grid.grid[pos]
                    
                    # Check if other group also trying
                    other_group = 3 - group  # 1->2, 2->1
                    other_trying = len(groups.get(other_group, []))
                    
                    if other_trying == 2 and gold_available >= 2:
                        # Both groups get gold
                        gold_available = 2
                    elif other_trying == 2 and gold_available == 1:
                        # Conflict, both fail
                        continue
                    
                    if gold_available > 0:
                        # Successful pickup
                        self.grid.grid[pos] -= 1
                        self.pickup_counts[group] += 1
                        
                        robots_at_pos[0].holding_gold = True
                        robots_at_pos[1].holding_gold = True
                        # Robot states are updated by the robots themselves
                        
                        print(f"DEBUG: Group {group} picked up gold at {pos}")
        
        # Execute movement actions
        new_positions = {}
        for robot in all_robots:
            if actions[robot.id] not in ["pickup", "idle"]:
                old_pos = robot.position
                robot.execute_action(actions[robot.id])
                new_positions[robot.id] = (old_pos, robot.position)
        
        # Check if carrying pairs moved together
        for robot in all_robots:
            if robot.holding_gold and robot.carrying_with:
                partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
                
                # Gold must be dropped if partner doesn't exist, doesn't have gold, or is at different position
                should_drop = False
                drop_reason = ""
                
                if not partner:
                    should_drop = True
                    drop_reason = "partner not found"
                elif not partner.holding_gold:
                    should_drop = True
                    drop_reason = "partner not holding gold"
                elif robot.position != partner.position:
                    should_drop = True
                    drop_reason = "partners separated"
                
                if should_drop:
                    # Dropped gold!
                    drop_pos = new_positions.get(robot.id, (robot.position, robot.position))[0]
                    self.grid.grid[drop_pos] = 1
                    
                    robot.holding_gold = False
                    robot.carrying_with = None
                    
                    if partner:
                        partner.holding_gold = False
                        partner.carrying_with = None
                        partner._reset_to_exploring()
                    
                    # Reset to exploring
                    robot._reset_to_exploring()
                    
                    print(f"DEBUG: Gold dropped at {drop_pos} - {drop_reason} (R{robot.id})")
        
        # Check for deposits
        for robot in all_robots:
            if robot.state == "at_deposit" and robot.holding_gold:
                deposit_pos = robot.get_deposit_pos()
                if robot.position == deposit_pos:
                    partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
                    if partner and partner.position == deposit_pos and partner.holding_gold:
                        # Successful deposit!
                        self.scores[robot.group] += 1
                        print(f"DEBUG: Group {robot.group} scored! Robots {robot.id} & {partner.id}")
                        
                        robot.holding_gold = False
                        partner.holding_gold = False
                        robot.carrying_with = None
                        partner.carrying_with = None
                        robot.target_gold_pos = None
                        partner.target_gold_pos = None
                        
                        # Reset to exploring to find more gold
                        robot._reset_to_exploring()
                        partner._reset_to_exploring()

    def _print_grid(self):
        """Print a visual representation of the grid"""
        print("\nGrid View:")
        print("Legend: R1=Group1 (red), R2=Group2 (blue), *=carrying, ↑=N, ↓=S, →=E, ←=W, G=Gold, D1/D2=Deposit")
        print("-" * 50)
        
        display_grid = [["." for _ in range(self.grid.size)] for _ in range(self.grid.size)]
        
        RED = "\033[31m"
        BLUE = "\033[34m"
        YELLOW = "\033[33m"
        GREEN = "\033[32m"
        RESET = "\033[0m"
        
        display_grid[0][0] = 'D1'
        display_grid[self.grid.size-1][self.grid.size-1] = 'D2'
        
        for i in range(self.grid.size):
            for j in range(self.grid.size):
                if self.grid.grid[i, j] > 0 and (i, j) not in [(0, 0), (self.grid.size-1, self.grid.size-1)]:
                    display_grid[i][j] = f'{YELLOW}G{int(self.grid.grid[i, j])}{RESET}'
        
        all_robots = self.group1 + self.group2
        
        # Group robots by position to show overlapping
        position_map = {}
        for robot in all_robots:
            pos = robot.position
            if pos not in position_map:
                position_map[pos] = []
            position_map[pos].append(robot)
        
        for pos, robots_at_pos in position_map.items():
            x, y = pos
            if len(robots_at_pos) == 1:
                robot = robots_at_pos[0]
                direction_symbol = {'N': '↑', 'S': '↓', 'E': '→', 'W': '←'}[robot.direction]
                color = RED if robot.group == 1 else BLUE
                
                if robot.holding_gold:
                    display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}*{RESET}'
                else:
                    display_grid[x][y] = f'{color}R{robot.group}{direction_symbol}{RESET}'
            else:
                # Multiple robots at same position
                group1_count = sum(1 for r in robots_at_pos if r.group == 1)
                group2_count = sum(1 for r in robots_at_pos if r.group == 2)
                carrying = any(r.holding_gold for r in robots_at_pos)
                
                if group1_count > 0 and group2_count > 0:
                    display_grid[x][y] = f'{GREEN}MIX{group1_count}{group2_count}{"*" if carrying else ""}{RESET}'
                elif group1_count > 1:
                    display_grid[x][y] = f'{RED}R1x{group1_count}{"*" if carrying else ""}{RESET}'
                elif group2_count > 1:
                    display_grid[x][y] = f'{BLUE}R2x{group2_count}{"*" if carrying else ""}{RESET}'
        
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
