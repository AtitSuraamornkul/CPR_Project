import random
import time
import numpy as np
from enum import Enum
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from collections import defaultdict

def strip_ansi(text):
    """Remove ANSI escape codes from text"""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class Direction(Enum):
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)

@dataclass
class PaxosMessage:
    """Message for Paxos consensus protocol"""
    msg_type: str  # 'prepare', 'promise', 'accept', 'accepted'
    proposal_id: int
    sender_id: int
    value: Optional[any] = None
    accepted_id: Optional[int] = None
    accepted_value: Optional[any] = None

class Grid:
    def __init__(self, size=20, num_gold=30):
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
            while True:
                x, y = random.randint(0, self.size-1), random.randint(0, self.size-1)
                if self.grid[x, y] == 0:  # Place gold only on empty cells
                    self.grid[x, y] = 1
                    break

    def get_cell(self, pos):
        x, y = pos
        if 0 <= x < self.size and 0 <= y < self.size:
            return self.grid[x, y]
        return -1

    def update_cell(self, pos, value):
        x, y = pos
        if 0 <= x < self.size and 0 <= y < self.size:
            self.grid[x, y] = value

class Robot:
    def __init__(self, robot_id: int, group: int, position: Tuple[int, int], direction: str, grid_size: int = 20):
        self.id = robot_id
        self.group = group
        self.position = position  # (x, y)
        self.direction = direction  # 'N', 'S', 'E', 'W'
        self.grid_size = grid_size
        
        # State machine states: 
        # "idle" -> exploring/searching
        # "moving_to_gold" -> found gold, moving towards it
        # "waiting_at_gold" -> at gold position, waiting for partner
        # "ready_to_pickup" -> partner arrived, ready to pickup
        # "carrying_gold" -> holding gold with partner, moving to deposit
        # "at_deposit" -> reached deposit with gold
        self.state = "idle"
        self.holding_gold = False
        self.carrying_with: Optional[int] = None
        self.target_gold_pos: Optional[Tuple[int, int]] = None
        self.next_action: Optional[str] = None
        
        # Paxos state
        self.proposal_number = 0
        self.highest_proposal_seen = -1
        self.accepted_proposal = -1
        self.accepted_value = None
        
        # Communication
        self.message_inbox: List[Dict] = []
        self.message_outbox: List[Dict] = []
        
        # Observations
        self.observed_gold: List[Tuple[int, int]] = []
        self.known_robots: Dict[int, Tuple[int, int]] = {}
        self.partner_agreed_action: Optional[str] = None
        
    def get_deposit_pos(self):
        """Get deposit position for this robot's group"""
        return (0, 0) if self.group == 1 else (self.grid_size - 1, self.grid_size - 1)
    
    def observe(self, grid_state: np.ndarray, all_robots: List['Robot']):
        """Observe visible positions based on direction (3 front + 5 further)"""
        self.observed_gold = []
        x, y = self.position
        
        # Get direction vectors
        dir_map = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
        dx, dy = dir_map[self.direction]
        
        # Perpendicular directions
        if self.direction in ['N', 'S']:
            perp = [(1, 0), (-1, 0)]  # East, West
        else:
            perp = [(0, 1), (0, -1)]  # South, North
        
        # Front row (3 positions)
        front_x, front_y = x + dx, y + dy
        for offset_dx, offset_dy in [(-perp[0][0], -perp[0][1]), (0, 0), perp[0]]:
            pos = (front_x + offset_dx, front_y + offset_dy)
            if self._is_valid_pos(pos) and grid_state[pos] == 1:
                self.observed_gold.append(pos)
        
        # Second row (5 positions)
        front2_x, front2_y = front_x + dx, front_y + dy
        for i in range(-2, 3):
            pos = (front2_x + i * perp[0][0], front2_y + i * perp[0][1])
            if self._is_valid_pos(pos) and grid_state[pos] == 1:
                self.observed_gold.append(pos)
        
        # Update known robot positions
        for robot in all_robots:
            if robot.group == self.group and robot.id != self.id:
                self.known_robots[robot.id] = robot.position
    
    def _is_valid_pos(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.grid_size and 0 <= y < self.grid_size
    
    def get_next_proposal_number(self):
        """Generate unique proposal number"""
        self.proposal_number += 1
        return self.proposal_number * 100 + self.id
    
    def process_messages(self, all_robots: List['Robot']):
        """Process incoming messages"""
        for msg in self.message_inbox:
            if msg["type"] == "partner_request":
                # Someone wants to partner with us
                sender_id = msg["sender_id"]
                gold_pos = tuple(msg["content"]["gold_pos"])
                
                # If we're idle or also targeting this gold, accept
                if self.state in ["idle", "moving_to_gold", "waiting_at_gold"] and not self.holding_gold:
                    self.carrying_with = sender_id
                    self.target_gold_pos = gold_pos
                    self.state = "moving_to_gold"
                    # Send confirmation
                    self.message_outbox.append({
                        "type": "partner_accept",
                        "sender_id": self.id,
                        "recipient_id": sender_id,
                        "content": {"gold_pos": gold_pos}
                    })
            
            elif msg["type"] == "partner_accept":
                # Partner accepted our request
                if not self.holding_gold:
                    self.carrying_with = msg["sender_id"]
                    self.state = "moving_to_gold"
            
            elif msg["type"] == "at_gold":
                # Partner has reached the gold
                if msg["sender_id"] == self.carrying_with:
                    if self.position == self.target_gold_pos:
                        self.state = "ready_to_pickup"
            
            elif msg["type"] == "ready_pickup":
                # Partner is ready to pickup
                if msg["sender_id"] == self.carrying_with:
                    if self.position == self.target_gold_pos and self.position == tuple(msg["content"]["pos"]):
                        self.state = "ready_to_pickup"
            
            elif msg["type"] == "propose_action":
                # Partner proposing an action (Paxos) - accept and store it
                proposal_id = msg["content"]["proposal_id"]
                action = msg["content"]["action"]
                
                if proposal_id >= self.highest_proposal_seen and msg["sender_id"] == self.carrying_with:
                    self.highest_proposal_seen = proposal_id
                    self.partner_agreed_action = action
                    # Automatically accept partner's proposal
                    self.message_outbox.append({
                        "type": "accept_action",
                        "sender_id": self.id,
                        "recipient_id": msg["sender_id"],
                        "content": {"proposal_id": proposal_id, "action": action}
                    })
            
            elif msg["type"] == "accept_action":
                # Partner accepted our proposed action (not needed for leader-follower)
                pass
            
            elif msg["type"] == "drop_gold":
                # Partner dropped the gold (moved wrong direction)
                if msg["sender_id"] == self.carrying_with:
                    self.holding_gold = False
                    self.carrying_with = None
                    self.state = "idle"
                    self.target_gold_pos = None
        
        self.message_inbox.clear()
    
    def decide_action(self, grid_state: np.ndarray, all_robots: List['Robot']) -> str:
        """Main decision logic based on state machine"""
        
        # STATE: carrying_gold - Move to deposit with partner
        if self.state == "carrying_gold" and self.holding_gold:
            deposit = self.get_deposit_pos()
            
            # Check if we're at deposit
            if self.position == deposit:
                # Check if partner is also at deposit
                partner = self._get_partner(all_robots)
                if partner and partner.position == deposit and partner.holding_gold:
                    self.state = "at_deposit"
                    return "idle"
                else:
                    # Wait for partner
                    return "idle"
            
            # Determine desired action to move towards deposit
            action = self._get_move_action_towards(deposit)

            # Both robots will calculate the same action since they are at the same
            # position and have the same goal. No need for communication here.
            return action
        
        # STATE: ready_to_pickup - Both robots at gold, attempt pickup
        if self.state == "ready_to_pickup":
            # Verify we're at the target gold position
            if self.position != self.target_gold_pos:
                self.state = "moving_to_gold"
                return self._get_move_action_towards(self.target_gold_pos)
            
            partner = self._get_partner(all_robots)
            if partner and partner.position == self.position and partner.position == self.target_gold_pos:
                # Check if partner is also ready OR at least waiting at gold
                if partner.state in ["ready_to_pickup", "waiting_at_gold"]:
                    # If partner is waiting, send ready signal again
                    if partner.state == "waiting_at_gold":
                        self.message_outbox.append({
                            "type": "ready_pickup",
                            "sender_id": self.id,
                            "recipient_id": self.carrying_with,
                            "content": {"pos": self.position}
                        })
                        # Wait for partner to become ready
                        return "idle"
                    else:
                        # Both ready, attempt pickup
                        print(f"DEBUG: R{self.id} and R{partner.id} both ready at {self.position}, attempting pickup")
                        return "pickup"
                else:
                    # Partner not in valid state
                    return "idle"
            else:
                # Partner not at same position, go back to waiting
                if partner:
                    print(f"DEBUG: R{self.id} ready but partner R{self.carrying_with} not at same position. Me:{self.position}, Partner:{partner.position}")
                else:
                    print(f"DEBUG: R{self.id} ready but partner R{self.carrying_with} not found")
                self.state = "waiting_at_gold"
                return "idle"
        
        # STATE: waiting_at_gold - At gold position, waiting for partner
        if self.state == "waiting_at_gold":
            # Check if we're actually at the target gold position
            if self.position != self.target_gold_pos:
                # Not at target yet, keep moving
                self.state = "moving_to_gold"
                return self._get_move_action_towards(self.target_gold_pos)
            
            partner = self._get_partner(all_robots)
            if partner and partner.position == self.position:
                # Partner arrived! Transition to ready
                self.state = "ready_to_pickup"
                # Notify partner we're ready
                self.message_outbox.append({
                    "type": "ready_pickup",
                    "sender_id": self.id,
                    "recipient_id": self.carrying_with,
                    "content": {"pos": self.position}
                })
                
                # If partner is already ready, we can pickup next turn
                if partner.state == "ready_to_pickup":
                    print(f"DEBUG: R{self.id} became ready, partner R{partner.id} already ready at {self.position}")
                
                return "idle"
            
            # Check if gold still there
            if not grid_state[self.target_gold_pos] > 0:
                # Gold gone, reset
                print(f"DEBUG: R{self.id} gold at {self.target_gold_pos} disappeared, resetting")
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
            
            return "idle"
        
        # STATE: moving_to_gold - Moving towards gold target
        if self.state == "moving_to_gold" and self.target_gold_pos:
            # Check if we reached the gold
            if self.position == self.target_gold_pos:
                self.state = "waiting_at_gold"
                # Notify partner we're here
                if self.carrying_with is not None:
                    self.message_outbox.append({
                        "type": "at_gold",
                        "sender_id": self.id,
                        "recipient_id": self.carrying_with,
                        "content": {"pos": self.position}
                    })
                
                # Check if partner is already here
                partner = self._get_partner(all_robots)
                if partner and partner.position == self.position and partner.state in ["waiting_at_gold", "ready_to_pickup"]:
                    self.state = "ready_to_pickup"
                    # Notify partner we're ready
                    self.message_outbox.append({
                        "type": "ready_pickup",
                        "sender_id": self.id,
                        "recipient_id": self.carrying_with,
                        "content": {"pos": self.position}
                    })
                
                return "idle"
            
            # Check if gold still exists
            if not grid_state[self.target_gold_pos] > 0:
                # Gold taken by others, reset
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
                return "idle"
            
            # Move towards gold
            return self._get_move_action_towards(self.target_gold_pos)
        
        # STATE: idle - Search for gold
        if self.state == "idle":
            # Look for gold in observed positions
            if self.observed_gold:
                # Pick closest gold
                target = min(self.observed_gold, 
                           key=lambda g: abs(g[0]-self.position[0]) + abs(g[1]-self.position[1]))
                self.target_gold_pos = target
                self.state = "moving_to_gold"
                
                # Look for available partner
                partner = self._find_available_partner(all_robots)
                if partner:
                    self.carrying_with = partner.id
                    # Send partner request
                    self.message_outbox.append({
                        "type": "partner_request",
                        "sender_id": self.id,
                        "recipient_id": partner.id,
                        "content": {"gold_pos": target}
                    })
                
                return self._get_move_action_towards(target)
            
            # Random exploration
            if random.random() < 0.2:
                return random.choice(["turn_left", "turn_right"])
            return "move"
        
        return "idle"
    
    def _get_partner(self, all_robots: List['Robot']) -> Optional['Robot']:
        """Get partner robot object"""
        if self.carrying_with is None:
            return None
        return next((r for r in all_robots if r.id == self.carrying_with), None)
    
    def _find_available_partner(self, all_robots: List['Robot']) -> Optional['Robot']:
        """Find an available teammate"""
        for robot in all_robots:
            if (robot.group == self.group and 
                robot.id != self.id and 
                robot.state == "idle" and
                not robot.holding_gold and
                robot.carrying_with == None):
                return robot
        return None
    
    def _get_move_action_towards(self, target: Tuple[int, int]) -> str:
        """Get action to move towards target"""
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        
        # Determine desired direction
        if abs(dx) > abs(dy):
            desired = 'E' if dx > 0 else 'W'
        else:
            desired = 'N' if dy < 0 else 'S'
        
        # Turn towards desired direction if needed
        if self.direction != desired:
            if self._should_turn_left(desired):
                return "turn_left"
            else:
                return "turn_right"
        
        return "move"
    
    def _should_turn_left(self, target_dir: str) -> bool:
        """Determine if should turn left"""
        dirs = ['N', 'E', 'S', 'W']
        current_idx = dirs.index(self.direction)
        target_idx = dirs.index(target_dir)
        
        left_turns = (current_idx - target_idx) % 4
        right_turns = (target_idx - current_idx) % 4
        
        return left_turns <= right_turns
    
    def execute_action(self, action: str):
        """Execute the decided action"""
        if action == "move":
            dir_map = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
            dx, dy = dir_map[self.direction]
            new_pos = (self.position[0] + dx, self.position[1] + dy)
            if self._is_valid_pos(new_pos):
                # If carrying gold, check if partner is moving with us
                if self.holding_gold and self.carrying_with:
                    # This will be validated in simulation
                    pass
                self.position = new_pos
        elif action == "turn_left":
            dirs = ['N', 'W', 'S', 'E']
            idx = dirs.index(self.direction)
            self.direction = dirs[(idx + 1) % 4]
        elif action == "turn_right":
            dirs = ['N', 'E', 'S', 'W']
            idx = dirs.index(self.direction)
            self.direction = dirs[(idx + 1) % 4]
    
    def update(self, grid_state: np.ndarray, all_robots: List['Robot']):
        """Main update loop: observe, process messages, decide, execute"""
        # Observe environment
        self.observe(grid_state, all_robots)
        
        # Process messages
        self.process_messages(all_robots)
        
        # Decide action
        action = self.decide_action(grid_state, all_robots)
        
        # Store action for simulation to process
        self.next_action = action

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

            # Process messages
            self._process_messages(all_robots)

            # Update all robots (observe, decide)
            for robot in all_robots:
                robot.update(self.grid.grid, all_robots)

            # Execute actions and handle game mechanics
            self._execute_actions(all_robots)

            # Print grid view
            self._print_grid()
            
            # Print robot states
            states = []
            for r in all_robots:
                states.append(f"R{r.id}@{r.position}: {r.state}, partner={r.carrying_with}, gold={r.holding_gold}, target={r.target_gold_pos}")
            print(f"Robot details:")
            for s in states:
                print(f"  {s}")
            print(f"Scores - Group 1: {self.scores[1]}, Group 2: {self.scores[2]}")
            print(f"Pickups - Group 1: {self.pickup_counts[1]}, Group 2: {self.pickup_counts[2]}")

            if step < self.steps - 1:
                time.sleep(0.15)
        
        self._print_final_results()

    def _process_messages(self, all_robots):
        """Deliver messages between robots"""
        messages_to_deliver = []
        for robot in all_robots:
            messages_to_deliver.extend(robot.message_outbox)
            robot.message_outbox = []

        for msg in messages_to_deliver:
            # Handle gold drop messages
            if msg["type"] == "drop_gold":
                pos = tuple(msg["content"]["pos"])
                if self.grid.grid[pos] == 0:
                    self.grid.grid[pos] = 1
                    print(f"DEBUG: Gold dropped at {pos}")

            # Deliver messages to recipients
            for robot in all_robots:
                if msg.get("broadcast"):
                    sender = next((r for r in all_robots if r.id == msg["sender_id"]), None)
                    if sender and robot.group == sender.group and robot.id != msg["sender_id"]:
                        robot.message_inbox.append(msg)
                elif "recipient_id" in msg and robot.id == msg["recipient_id"]:
                    robot.message_inbox.append(msg)

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
                        robots_at_pos[0].state = "carrying_gold"
                        robots_at_pos[1].state = "carrying_gold"
                        
                        # Ensure they're partners
                        robots_at_pos[0].carrying_with = robots_at_pos[1].id
                        robots_at_pos[1].carrying_with = robots_at_pos[0].id
                        
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
                if partner and partner.holding_gold:
                    # Both must have moved to same position
                    if robot.position != partner.position:
                        # Dropped gold!
                        drop_pos = new_positions.get(robot.id, (robot.position, robot.position))[0]
                        self.grid.grid[drop_pos] = 1
                        
                        robot.holding_gold = False
                        partner.holding_gold = False
                        robot.state = "idle"
                        partner.state = "idle"
                        robot.carrying_with = None
                        partner.carrying_with = None
                        
                        print(f"DEBUG: Gold dropped at {drop_pos} - partners separated")
        
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
                        robot.state = "idle"
                        partner.state = "idle"
                        robot.carrying_with = None
                        partner.carrying_with = None
                        robot.target_gold_pos = None
                        partner.target_gold_pos = None

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

def main():
    # Initialize grid
    grid = Grid(size=20, num_gold=10)
    
    # Initialize robots
    group1 = []
    group2 = []
    
    for i in range(10):
        # Group 1 robots start near top-left
        x = random.randint(0, 4)
        y = random.randint(0, 4)
        direction = random.choice(['N', 'S', 'E', 'W'])
        robot = Robot(i, 1, (x, y), direction)
        group1.append(robot)
        
        # Group 2 robots start near bottom-right
        x = random.randint(15, 19)
        y = random.randint(15, 19)
        direction = random.choice(['N', 'S', 'E', 'W'])
        robot = Robot(i + 10, 2, (x, y), direction)
        group2.append(robot)
    
    # Run simulation
    sim = Simulation(grid, group1, group2, steps=500)
    sim.run()

if __name__ == "__main__":
    main()