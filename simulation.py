"""
Simulation class for running the robot gold collection game
"""
import random
from collections import defaultdict
import time
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
        self.delayed_messages = []  # List of (delivery_step, message)
        self.current_step = 0
        
        # Maps frozenset of robot IDs to the position where gold was picked up
        self.physical_gold_carriers = {}  # {frozenset({id1, id2}): pickup_position}

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
                # Calculate visible cells outside the robot
                visible_cells = {}

                for pos in robot.get_visible_positions():
                    visible_cells[pos] = self.grid.get_cell(pos)
                # 2. Tactile Sensing (Current position) - 1 cell
                visible_cells[robot.position] = self.grid.get_cell(robot.position)
                
                # 3. Robot can sense if it's physically carrying gold
                physical_holding_gold = self._is_robot_physically_carrying(robot.id)
                
                robot.update(visible_cells, physical_holding_gold)

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
            #    time.sleep(0.05)
            
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
            # Add random delay to message delivery
            delay = random.randint(self.message_delay_range[0], self.message_delay_range[1])
            delivery_step = self.current_step + delay
            self.delayed_messages.append((delivery_step, msg))
            
            # print debug info for finder-helper messages to see delays
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
                        # Successful pickup - update physical state only
                        self.grid.grid[pos] -= 1
                        self.pickup_counts[group] += 1
                        
                        # Track physical gold carriers (physics state)
                        robot_pair = frozenset({robots_at_pos[0].id, robots_at_pos[1].id})
                        self.physical_gold_carriers[robot_pair] = pos
                        
                        # Robots will sense this via physical_holding_gold in their update()
                        print(f"DEBUG: Group {group} picked up gold at {pos} (physical)")
        
        # Execute movement actions and track all robot positions
        new_positions = {}
        for robot in all_robots:
            old_pos = robot.position
            if actions[robot.id] not in ["pickup", "idle"]:
                robot.execute_action(actions[robot.id])
            # Track all robots, even if they didn't move
            new_positions[robot.id] = (old_pos, robot.position)
        
        # Check if carrying pairs physically separated (physics enforcement)
        pairs_to_drop = []
        for robot_pair, pickup_pos in list(self.physical_gold_carriers.items()):
            robot_ids = list(robot_pair)
            robot1 = next((r for r in all_robots if r.id == robot_ids[0]), None)
            robot2 = next((r for r in all_robots if r.id == robot_ids[1]), None)
            
            # Gold must be dropped if partners are at different positions
            should_drop = False
            drop_pos = None
            drop_reason = ""
            
            if not robot1 or not robot2:
                should_drop = True
                drop_reason = "robot not found"
                # Drop at the position of the robot that still exists
                drop_pos = robot1.position if robot1 else (robot2.position if robot2 else pickup_pos)
            elif robot1.position != robot2.position:
                should_drop = True
                drop_reason = "partners separated"
                # Drop at the old position before movement (first element of tuple)
                drop_pos = new_positions[robot1.id][0]
            
            if should_drop:
                # Drop gold physically (update grid)
                self.grid.grid[drop_pos] = 1
                pairs_to_drop.append(robot_pair)
                print(f"DEBUG: Gold dropped physically at {drop_pos} - {drop_reason} (R{robot_ids[0]}, R{robot_ids[1]})")
        
        # Remove dropped gold from physical tracking
        for robot_pair in pairs_to_drop:
            del self.physical_gold_carriers[robot_pair]
        
        # Check for deposits (physics enforcement)
        pairs_to_deposit = []
        for robot_pair in list(self.physical_gold_carriers.keys()):
            robot_ids = list(robot_pair)
            robot1 = next((r for r in all_robots if r.id == robot_ids[0]), None)
            robot2 = next((r for r in all_robots if r.id == robot_ids[1]), None)
            
            if robot1 and robot2:
                # Check if both robots are at their deposit position
                deposit_pos = robot1.get_deposit_pos()
                if robot1.position == deposit_pos and robot2.position == deposit_pos:
                    # Successful deposit Update score and remove physical gold
                    self.scores[robot1.group] += 1
                    pairs_to_deposit.append(robot_pair)
                    print(f"DEBUG: Group {robot1.group} scored! Robots {robot1.id} & {robot2.id} (physical)")
        
        # Remove deposited gold from physical tracking
        for robot_pair in pairs_to_deposit:
            del self.physical_gold_carriers[robot_pair]

    def _is_robot_physically_carrying(self, robot_id: int) -> bool:
        """Check if a robot is physically carrying gold (physics state)"""
        for robot_pair in self.physical_gold_carriers.keys():
            if robot_id in robot_pair:
                return True
        return False
    
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
