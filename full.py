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

# Finder-Helper Protocol (from new.md)
# Messages: found, response, ack, here, ack2

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
        # "exploring" -> searching for gold
        # "finder_waiting_response" -> sent found message, waiting for response
        # "finder_waiting_here" -> sent ack, waiting for helper at opposite
        # "finder_ready" -> helper at opposite, ready to move to gold
        # "helper_waiting_ack" -> sent response, waiting for ack
        # "helper_moving_opposite" -> acknowledged, moving to opposite position
        # "helper_waiting_ack2" -> at opposite, sent here, waiting for ack2
        # "moving_to_gold" -> moving to gold position
        # "waiting_at_gold" -> at gold, waiting for partner
        # "ready_to_pickup" -> both at gold, ready to pickup
        # "carrying_gold" -> holding gold, moving to deposit
        # "at_deposit" -> at deposit with gold
        self.state = "exploring"
        self.holding_gold = False
        self.carrying_with: Optional[int] = None
        self.target_gold_pos: Optional[Tuple[int, int]] = None
        self.next_action: Optional[str] = None
        
        # Finder-Helper Protocol State
        self.role = 'exploring'  # 'exploring', 'finder', 'helper'
        self.message_index = 0  # Unique index for each found message
        self.finder_id: Optional[int] = None
        self.helper_id: Optional[int] = None
        self.current_message_index: Optional[int] = None  # Track current conversation
        self.timeout_counter = 0
        self.max_timeout = 15  # Steps before retrying

        # State-related timers
        self.wait_timer = 0
        self.pickup_timer = 0

        # Communication
        self.message_inbox: List[Dict] = []
        self.message_outbox: List[Dict] = []
        
        # Observations
        self.observed_gold: List[Tuple[int, int]] = []
        self.teammate_states: Dict[int, Dict[str, Any]] = {} # Caches the last known state of teammates
        
    def get_deposit_pos(self):
        """Get deposit position for this robot's group"""
        return (0, 0) if self.group == 1 else (self.grid_size - 1, self.grid_size - 1)
    
    def get_visible_positions(self) -> List[Tuple[int, int]]:
        """Calculate visible positions based on direction"""
        visible = []
        x, y = self.position
        # Coordinates are (row, col). Interpret directions as:
        # N: up (row-1), S: down (row+1), E: right (col+1), W: left (col-1)
        dir_map = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
        dx, dy = dir_map[self.direction]
        
        # Perpendicular offsets: for vertical motion, vary columns; for
        # horizontal motion, vary rows.
        if self.direction in ['N', 'S']:
            perp = [(0, 1), (0, -1)]  # right, left
        else:
            perp = [(1, 0), (-1, 0)]  # down, up
            
        # Front row
        front_x, front_y = x + dx, y + dy
        for offset_dx, offset_dy in [(-perp[0][0], -perp[0][1]), (0, 0), perp[0]]:
            pos = (front_x + offset_dx, front_y + offset_dy)
            if self._is_valid_pos(pos):
                visible.append(pos)
                
        # Second row
        front2_x, front2_y = front_x + dx, front_y + dy
        for i in range(-2, 3):
            pos = (front2_x + i * perp[0][0], front2_y + i * perp[0][1])
            if self._is_valid_pos(pos):
                visible.append(pos)
        return visible

    def observe(self, visible_cells: Dict[Tuple[int, int], int]):
        """Observe visible positions based on direction (3 front + 5 further)"""
        self.observed_gold = []
        # We strictly use the passed visible_cells which contains the "slice" of reality
        visible_pos = self.get_visible_positions()
        
        for pos in visible_pos:
            # Only record gold if it's in our provided view (it should be) and equals 1
            if pos in visible_cells and visible_cells[pos] == 1:
                self.observed_gold.append(pos)
    
    def _is_valid_pos(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.grid_size and 0 <= y < self.grid_size
    
    def process_messages(self):
        """Process incoming messages using finder-helper protocol"""
        for msg in self.message_inbox:
            msg_type = msg.get("type")
            sender_id = msg.get("sender_id")
            content = msg.get("content", {})

            if msg_type == "state_update":
                teammate_id = msg["sender_id"]
                self.teammate_states[teammate_id] = msg["content"]

            # FINDER-HELPER PROTOCOL MESSAGES
            elif msg_type == "found":
                # Robot exploring receives found message from potential finder
                if self.role == 'exploring' and self.state == "exploring":
                    finder_id = content.get("finder_id")
                    msg_index = content.get("index")
                    gold_pos = tuple(content.get("gold_pos"))
                    finder_pos = tuple(content.get("finder_pos"))
                    
                    # Send response to offer help
                    self.message_outbox.append({
                        "type": "response",
                        "sender_id": self.id,
                        "recipient_id": finder_id,
                        "content": {
                            "helper_id": self.id,
                            "finder_id": finder_id,
                            "index": msg_index
                        }
                    })
                    self.state = "helper_waiting_ack"
                    self.role = 'helper'
                    self.finder_id = finder_id
                    self.target_gold_pos = gold_pos
                    self.current_message_index = msg_index

            elif msg_type == "response":
                # Finder receives response from potential helper
                if self.role == 'finder' and self.state == "finder_waiting_response":
                    helper_id = content.get("helper_id")
                    msg_index = content.get("index")
                    
                    if msg_index == self.current_message_index:
                        # Accept first response
                        self.helper_id = helper_id
                        self.carrying_with = helper_id
                        self.message_outbox.append({
                            "type": "ack",
                            "sender_id": self.id,
                            "recipient_id": helper_id,
                            "content": {
                                "finder_id": self.id,
                                "helper_id": helper_id,
                                "index": msg_index
                            }
                        })
                        self.state = "finder_waiting_here"
                        self.timeout_counter = 0

            elif msg_type == "ack":
                # Helper receives ack from finder (selected!)
                if self.role == 'helper' and self.state == "helper_waiting_ack":
                    helper_id = content.get("helper_id")
                    msg_index = content.get("index")
                    
                    if helper_id == self.id and msg_index == self.current_message_index:
                        # I was selected!
                        self.carrying_with = self.finder_id
                        self.state = "helper_moving_opposite"
                        self.timeout_counter = 0
                    elif msg_index == self.current_message_index:
                        # Someone else was selected
                        self.role = 'exploring'
                        self.state = "exploring"
                        self.finder_id = None
                        self.target_gold_pos = None
                        self.current_message_index = None

            elif msg_type == "here":
                # Finder receives here message (helper at opposite position)
                if self.role == 'finder' and self.state == "finder_waiting_here":
                    helper_id = content.get("helper_id")
                    msg_index = content.get("index")
                    
                    if helper_id == self.helper_id and msg_index == self.current_message_index:
                        self.state = "finder_ready"
                        self.timeout_counter = 0

            elif msg_type == "ack2":
                # Helper receives ack2 from finder (ready to pickup)
                if self.role == 'helper' and self.state == "helper_waiting_ack2":
                    msg_index = content.get("index")
                    
                    if msg_index == self.current_message_index:
                        self.state = "moving_to_gold"
                        self.timeout_counter = 0
        
        self.message_inbox.clear()
    
    def decide_action(self, visible_cells: Dict[Tuple[int, int], int]) -> str:
        """Main decision logic based on finder-helper protocol state machine"""
        
        # CARRYING GOLD - move to deposit
        if self.state == "carrying_gold" and self.holding_gold:
            deposit = self.get_deposit_pos()
            if self.position == deposit:
                # Immediately transition to at_deposit when we reach the deposit
                # The simulation's _execute_actions will handle checking if both robots are physically present
                self.state = "at_deposit"
                return "idle"
            
            return self._get_move_action_towards(deposit)
        
        # READY TO PICKUP - execute pickup
        if self.state == "ready_to_pickup":
            # Transition to carrying_gold if pickup was successful
            if self.holding_gold:
                self.state = "carrying_gold"
                self.pickup_timer = 0
                return "idle"
            
            # Timeout if stuck (likely due to crowding - more than 2 robots at same location)
            self.pickup_timer += 1
            if self.pickup_timer > 5:
                print(f"DEBUG: R{self.id} timed out in ready_to_pickup (likely crowding), resetting")
                self._reset_to_exploring()
                return "idle"
            
            return "pickup"
        
        # WAITING AT GOLD - wait for partner to arrive
        if self.state == "waiting_at_gold":
            # Check if partner is here
            if self.carrying_with in self.teammate_states:
                partner_state = self.teammate_states[self.carrying_with]
                # Check if partner is at the same position and also waiting
                # We rely on received state updates
                if (tuple(partner_state.get("position")) == self.position and 
                    partner_state.get("state") in ["waiting_at_gold", "ready_to_pickup"]):
                    self.state = "ready_to_pickup"
                    self.pickup_timer = 0  # Reset timer when entering this state
                    return "idle"

            # Check if gold still exists (using local sensing)
            # Since we are at the position, we can sense it directly (if passed in visible_cells)
            if self.position in visible_cells:
                 if not visible_cells[self.position] > 0:
                     self._reset_to_exploring()
                     return "idle"
            
            # Timeout after waiting too long
            self.wait_timer += 1
            if self.wait_timer > 30:
                print(f"DEBUG: R{self.id} timed out waiting at gold, resetting")
                self._reset_to_exploring()
                self.wait_timer = 0
                return "idle"
            
            return "idle"
        
        # MOVING TO GOLD - navigate to gold position
        if self.state == "moving_to_gold" and self.target_gold_pos:
            if self.position == self.target_gold_pos:
                self.state = "waiting_at_gold"
                self.wait_timer = 0  # Reset timer when arriving
                return "idle"
            
            # Check if gold is missing (only if visible)
            if self.target_gold_pos in visible_cells:
                if not visible_cells[self.target_gold_pos] > 0:
                    # Gold gone, reset
                    self._reset_to_exploring()
                    return "idle"
            
            return self._get_move_action_towards(self.target_gold_pos)
        
        # FINDER STATES
        if self.state == "finder_waiting_response":
            # Timeout and retry
            self.timeout_counter += 1
            if self.timeout_counter > self.max_timeout:
                # Retry sending found message
                self._send_found_message()
                self.timeout_counter = 0
            return "idle"
        
        if self.state == "finder_waiting_here":
            # Wait for helper to reach opposite position
            self.timeout_counter += 1
            if self.timeout_counter > self.max_timeout:
                # Timeout, reset
                self._reset_to_exploring()
            return "idle"
        
        if self.state == "finder_ready":
            # Move to gold and send ack2
            if self.position == self.target_gold_pos:
                # Already at gold, send ack2
                self.message_outbox.append({
                    "type": "ack2",
                    "sender_id": self.id,
                    "recipient_id": self.helper_id,
                    "content": {
                        "finder_id": self.id,
                        "helper_id": self.helper_id,
                        "index": self.current_message_index
                    }
                })
                self.state = "moving_to_gold"  # Will transition to waiting_at_gold
                return "idle"
            else:
                # Move to gold
                action = self._get_move_action_towards(self.target_gold_pos)
                # Once we start moving, send ack2
                if action == "move":
                    self.message_outbox.append({
                        "type": "ack2",
                        "sender_id": self.id,
                        "recipient_id": self.helper_id,
                        "content": {
                            "finder_id": self.id,
                            "helper_id": self.helper_id,
                            "index": self.current_message_index
                        }
                    })
                    self.state = "moving_to_gold"
                return action
        
        # HELPER STATES
        if self.state == "helper_waiting_ack":
            # Wait for ack or timeout
            self.timeout_counter += 1
            if self.timeout_counter > self.max_timeout:
                # Not selected, go back to exploring
                self._reset_to_exploring()
            return "idle"
        
        if self.state == "helper_moving_opposite":
            # Calculate opposite position
            if self.target_gold_pos:
                opposite_pos = self._get_opposite_position(self.target_gold_pos)
                
                if self.position == opposite_pos:
                    # Reached opposite, send here message
                    self.message_outbox.append({
                        "type": "here",
                        "sender_id": self.id,
                        "recipient_id": self.finder_id,
                        "content": {
                            "helper_id": self.id,
                            "finder_id": self.finder_id,
                            "index": self.current_message_index
                        }
                    })
                    self.state = "helper_waiting_ack2"
                    self.timeout_counter = 0
                    return "idle"
                
                return self._get_move_action_towards(opposite_pos)
            return "idle"
        
        if self.state == "helper_waiting_ack2":
            # Wait for ack2 from finder
            self.timeout_counter += 1
            if self.timeout_counter > self.max_timeout:
                # Timeout, reset
                self._reset_to_exploring()
            return "idle"
        
        # EXPLORING STATE - look for gold
        if self.state == "exploring":
            # If see gold, become finder
            if self.observed_gold and self.role == 'exploring':
                # Become finder
                self.role = 'finder'
                self.target_gold_pos = self.observed_gold[0]  # Pick first visible gold
                self.message_index += 1
                self.current_message_index = self.message_index
                self._send_found_message()
                self.state = "finder_waiting_response"
                self.timeout_counter = 0
                return "idle"
            
            # Random exploration
            if random.random() < 0.2:
                return random.choice(["turn_left", "turn_right"])
            return "move"
        
        return "idle"
    
    def _send_found_message(self):
        """Send found message to all teammates"""
        self.message_outbox.append({
            "type": "found",
            "sender_id": self.id,
            "broadcast": True,
            "content": {
                "finder_id": self.id,
                "index": self.current_message_index,
                "gold_pos": self.target_gold_pos,
                "finder_pos": self.position
            }
        })
    
    def _get_opposite_position(self, gold_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate opposite position across gold from finder"""
        # Simple heuristic: mirror across gold position
        gx, gy = gold_pos
        # Try positions adjacent to gold
        candidates = [(gx+1, gy), (gx-1, gy), (gx, gy+1), (gx, gy-1)]
        valid_candidates = [pos for pos in candidates if self._is_valid_pos(pos)]
        if valid_candidates:
            # Pick closest to current position
            return min(valid_candidates, key=lambda p: abs(p[0]-self.position[0]) + abs(p[1]-self.position[1]))
        return gold_pos
    
    def _reset_to_exploring(self):
        """Reset robot to exploring state"""
        self.role = 'exploring'
        self.state = "exploring"
        self.finder_id = None
        self.helper_id = None
        self.carrying_with = None
        self.target_gold_pos = None
        self.current_message_index = None
        self.timeout_counter = 0
        self.wait_timer = 0
        self.pickup_timer = 0
    
    def _get_move_action_towards(self, target: Tuple[int, int]) -> str:
        """Get action to move towards target"""
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        
        # Coordinates are (row, col). Rows correspond to N/S, columns to E/W.
        if abs(dx) > abs(dy):
            # Move mostly vertically
            desired = 'S' if dx > 0 else 'N'
        else:
            # Move mostly horizontally
            desired = 'E' if dy > 0 else 'W'
        
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
            # Move according to (row, col) convention
            dir_map = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
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
    
    def update(self, visible_cells: Dict[Tuple[int, int], int]):
        """Main update loop: observe, process messages, decide, execute"""
        self.observe(visible_cells)
        self.process_messages()
        action = self.decide_action(visible_cells)
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
                "role": self.role,
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
                if partner and partner.holding_gold:
                    # Both must have moved to same position
                    if robot.position != partner.position:
                        # Dropped gold!
                        drop_pos = new_positions.get(robot.id, (robot.position, robot.position))[0]
                        self.grid.grid[drop_pos] = 1
                        
                        robot.holding_gold = False
                        partner.holding_gold = False
                        robot.carrying_with = None
                        partner.carrying_with = None
                        
                        # Reset to exploring
                        robot._reset_to_exploring()
                        partner._reset_to_exploring()
                        
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