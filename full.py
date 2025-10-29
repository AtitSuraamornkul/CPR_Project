import random
import time
import numpy as np
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
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
    value: Optional[Any] = None
    accepted_id: Optional[int] = None
    accepted_value: Optional[Any] = None

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
        
        # Paxos state (fully decentralized - no leader role)
        self.proposal_number = 0
        self.highest_proposal_seen = -1
        self.accepted_proposal = -1
        self.accepted_value = None
        self.paxos_state = 'idle'  # idle, preparing, proposing, finished
        self.promises_received = set()
        self.accepts_received = set()
        self.current_plan = None
        self.proposal_backoff = 0  # Backoff timer before proposing again

        # State-related timers
        self.wait_timer = 0

        # Communication
        self.message_inbox: List[Dict] = []
        self.message_outbox: List[Dict] = []
        
        # Observations
        self.observed_gold: List[Tuple[int, int]] = []
        self.teammate_states: Dict[int, Dict[str, Any]] = {} # Caches the last known state of teammates
        
    def get_deposit_pos(self):
        """Get deposit position for this robot's group"""
        return (0, 0) if self.group == 1 else (self.grid_size - 1, self.grid_size - 1)
    
    def observe(self, grid_state: np.ndarray):
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
    
    def _is_valid_pos(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.grid_size and 0 <= y < self.grid_size
    
    def get_next_proposal_number(self):
        """Generate unique proposal number"""
        self.proposal_number += 1
        return self.proposal_number * 100 + self.id
    
    def process_messages(self):
        """Process incoming messages"""
        for msg in self.message_inbox:
            msg_type = msg.get("type")
            sender_id = msg.get("sender_id")
            content = msg.get("content", {})

            if msg_type == "state_update":
                teammate_id = msg["sender_id"]
                self.teammate_states[teammate_id] = msg["content"]

            elif msg_type == "paxos_prepare":
                proposal_id = content.get("proposal_id")
                if proposal_id >= self.highest_proposal_seen:
                    self.highest_proposal_seen = proposal_id
                    self.paxos_state = 'preparing' # Show we are engaged in a paxos round
                    self.message_outbox.append({
                        "type": "paxos_promise",
                        "sender_id": self.id,
                        "recipient_id": sender_id,
                        "content": {
                            "proposal_id": proposal_id,
                            "accepted_proposal": self.accepted_proposal,
                            "accepted_value": self.accepted_value
                        }
                    })

            elif msg_type == "paxos_promise":
                # Any robot initiating a proposal can receive promises
                if self.paxos_state == 'preparing':
                    proposal_id = content.get("proposal_id")
                    if proposal_id == self.highest_proposal_seen:
                        self.promises_received.add(sender_id)
                        if content.get("accepted_proposal", -1) > self.accepted_proposal:
                            self.accepted_proposal = content["accepted_proposal"]
                            self.accepted_value = content["accepted_value"]
                        
                        num_teammates = len(self.teammate_states) + 1
                        if len(self.promises_received) > num_teammates / 2:
                            self.paxos_state = 'proposing'
                            # Send ACCEPT to all known teammates and self
                            all_known_teammates = list(self.teammate_states.keys()) + [self.id]
                            for teammate_id in all_known_teammates:
                                self.message_outbox.append({
                                    "type": "paxos_accept",
                                    "sender_id": self.id,
                                    "recipient_id": teammate_id,
                                    "content": {
                                        "proposal_id": self.highest_proposal_seen,
                                        "value": self.accepted_value
                                    }
                                })
            
            elif msg_type == "paxos_accept":
                proposal_id = content.get("proposal_id")
                if proposal_id >= self.highest_proposal_seen:
                    self.accepted_proposal = proposal_id
                    self.accepted_value = content.get("value")
                    self.paxos_state = 'proposing'
                    self.message_outbox.append({
                        "type": "paxos_accepted",
                        "sender_id": self.id,
                        "recipient_id": sender_id,
                        "content": {"proposal_id": proposal_id}
                    })

            elif msg_type == "paxos_accepted":
                # Any robot proposing can receive accepts
                if self.paxos_state == 'proposing':
                    proposal_id = content.get("proposal_id")
                    if proposal_id == self.highest_proposal_seen:
                        self.accepts_received.add(sender_id)
                        
                        num_teammates = len(self.teammate_states) + 1
                        if len(self.accepts_received) > num_teammates / 2:
                            self.paxos_state = 'finished'
                            self.current_plan = self.accepted_value
                            
                            all_known_teammates = list(self.teammate_states.keys()) + [self.id]
                            for teammate_id in all_known_teammates:
                                self.message_outbox.append({
                                    "type": "paxos_commit",
                                    "sender_id": self.id,
                                    "recipient_id": teammate_id,
                                    "content": {"plan": self.current_plan}
                                })
                            
                            self.promises_received = set()
                            self.accepts_received = set()
                            self.proposal_backoff = 0

            elif msg_type == "paxos_commit":
                self.current_plan = content.get("plan")
                self.paxos_state = 'idle'
                self.proposal_backoff = 0  # Reset backoff when plan received
            
            elif msg_type == "at_gold":
                if sender_id == self.carrying_with:
                    if self.position == self.target_gold_pos:
                        self.state = "ready_to_pickup"
            
            elif msg_type == "ready_pickup":
                if sender_id == self.carrying_with:
                    if self.position == self.target_gold_pos and self.position == tuple(content["pos"]):
                        self.state = "ready_to_pickup"
            
            elif msg_type == "drop_gold":
                if sender_id == self.carrying_with:
                    self.holding_gold = False
                    self.carrying_with = None
                    self.state = "idle"
                    self.target_gold_pos = None
        
        self.message_inbox.clear()
    
    def decide_action(self, grid_state: np.ndarray) -> str:
        """Main decision logic based on state machine"""
        
        if self.state == "carrying_gold" and self.holding_gold:
            deposit = self.get_deposit_pos()
            if self.position == deposit:
                if self.carrying_with in self.teammate_states:
                    partner_state = self.teammate_states[self.carrying_with]
                    if partner_state.get("position") == self.position:
                        self.state = "at_deposit"
                        return "idle"
                return "idle"
            
            action = self._get_move_action_towards(deposit)
            return action
        
        if self.state == "ready_to_pickup":
            return "pickup"
        
        if self.state == "waiting_at_gold":
            self.wait_timer += 1
            if self.position != self.target_gold_pos:
                self.state = "moving_to_gold"
                self.wait_timer = 0
                return self._get_move_action_towards(self.target_gold_pos)
            
            if self.carrying_with in self.teammate_states:
                partner_state = self.teammate_states[self.carrying_with]
                if partner_state.get("position") == self.position and partner_state.get("state") in ["waiting_at_gold", "ready_to_pickup"]:
                    self.state = "ready_to_pickup"
                    self.wait_timer = 0
                    self.message_outbox.append({"type": "ready_pickup", "sender_id": self.id, "recipient_id": self.carrying_with, "content": {"pos": self.position}})
                    return "idle"
            
            if not grid_state[self.target_gold_pos] > 0:
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
                self.paxos_state = 'idle'
                self.wait_timer = 0
                return "idle"

            if self.wait_timer > 20:
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
                self.paxos_state = 'idle'
                self.wait_timer = 0
                return "idle"
            
            return "idle"
        
        if self.state == "moving_to_gold" and self.target_gold_pos:
            if self.position == self.target_gold_pos:
                self.state = "waiting_at_gold"
                if self.carrying_with is not None:
                    self.message_outbox.append({"type": "at_gold", "sender_id": self.id, "recipient_id": self.carrying_with, "content": {"pos": self.position}})
                
                if self.carrying_with in self.teammate_states:
                    partner_state = self.teammate_states[self.carrying_with]
                    if partner_state.get("position") == self.position and partner_state.get("state") in ["waiting_at_gold", "ready_to_pickup"]:
                        self.state = "ready_to_pickup"
                        self.message_outbox.append({"type": "ready_pickup", "sender_id": self.id, "recipient_id": self.carrying_with, "content": {"pos": self.position}})
                
                return "idle"
            
            if not grid_state[self.target_gold_pos] > 0:
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
                return "idle"
            
            return self._get_move_action_towards(self.target_gold_pos)
        
        if self.state == "idle":
            # Execute plan if we have one
            if self.current_plan and self.id in self.current_plan:
                assignment = self.current_plan[self.id]
                self.state = "moving_to_gold"
                self.target_gold_pos = assignment["gold_pos"]
                self.carrying_with = assignment["partner_id"]
                self.paxos_state = 'idle'
                self.current_plan = None
                return self._get_move_action_towards(self.target_gold_pos)

            # Decrement backoff timer
            if self.proposal_backoff > 0:
                self.proposal_backoff -= 1

            # DECENTRALIZED: Any idle robot can propose when they see gold
            idle_teammate_ids = [r_id for r_id, r_state in self.teammate_states.items() 
                               if r_state.get("state") == 'idle' and r_state.get("paxos_state") == 'idle']
            all_idle_ids = idle_teammate_ids + [self.id] if self.paxos_state == 'idle' else idle_teammate_ids

            if not all_idle_ids:
                return "move"

            # Any robot can initiate proposal if they observe gold and backoff has expired
            if self.observed_gold and self.paxos_state == 'idle' and self.proposal_backoff == 0:
                # Random chance to propose (reduces simultaneous proposals)
                if random.random() < 0.3:  # 30% chance to initiate
                    self.paxos_state = 'preparing'
                    available_robot_ids = all_idle_ids.copy()
                    available_gold = set(self.observed_gold)
                    plan = {}

                    while len(available_robot_ids) >= 2 and available_gold:
                        robot1_id = available_robot_ids.pop(0)
                        robot2_id = available_robot_ids.pop(0)
                        robot1_pos = self.position
                        target_gold = min(available_gold, key=lambda g: abs(g[0]-robot1_pos[0]) + abs(g[1]-robot1_pos[1]))
                        available_gold.remove(target_gold)
                        plan[robot1_id] = {"partner_id": robot2_id, "gold_pos": target_gold}
                        plan[robot2_id] = {"partner_id": robot1_id, "gold_pos": target_gold}

                    if plan:
                        proposal_id = self.get_next_proposal_number()
                        self.highest_proposal_seen = proposal_id
                        self.accepted_value = plan
                        for teammate_id in self.teammate_states.keys():
                            self.message_outbox.append({
                                "type": "paxos_prepare", 
                                "sender_id": self.id, 
                                "recipient_id": teammate_id, 
                                "content": {"proposal_id": proposal_id}
                            })
                        self.promises_received = {self.id}
                        # Set random backoff if proposal fails
                        self.proposal_backoff = random.randint(5, 15)
                    
                    return "idle"

            # Random exploration
            if random.random() < 0.2:
                return random.choice(["turn_left", "turn_right"])
            return "move"
        
        return "idle"
    
    def _get_move_action_towards(self, target: Tuple[int, int]) -> str:
        """Get action to move towards target"""
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        
        if abs(dx) > abs(dy):
            desired = 'E' if dx > 0 else 'W'
        else:
            desired = 'N' if dy < 0 else 'S'
        
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
                if self.holding_gold and self.carrying_with:
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
    
    def update(self, grid_state: np.ndarray):
        """Main update loop: observe, process messages, decide, execute"""
        self.observe(grid_state)
        self.process_messages()
        action = self.decide_action(grid_state)
        self.next_action = action
        self._broadcast_my_state()

    def _broadcast_my_state(self):
        """Broadcasts essential state to teammates."""
        state_message = {
            "type": "state_update",
            "sender_id": self.id,
            "broadcast": True,
            "content": {
                "state": self.state,
                "paxos_state": self.paxos_state,
                "position": self.position,
            }
        }
        self.message_outbox.append(state_message)
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
                robot.update(self.grid.grid)

            self._execute_actions(all_robots)

            self._print_grid()
            
            states = []
            for r in all_robots:
                states.append(f"R{r.id}@{r.position}: {r.state}, partner={r.carrying_with}, gold={r.holding_gold}, target={r.target_gold_pos}, paxos={r.paxos_state}, backoff={r.proposal_backoff}")
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

            if step < self.steps - 1:
               time.sleep(0.15)
            
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
                
                # Optional: print debug info for Paxos messages to see delays
                if msg["type"].startswith("paxos"):
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
    sim = Simulation(grid, group1, group2, steps=5000)
    sim.run()

if __name__ == "__main__":
    main()