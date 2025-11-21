"""
Robot class implementing the Finder-Helper protocol
"""
import random
from typing import List, Tuple, Optional, Dict, Any

# Messages: found, response, ack, here, ack2


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

        # N: up (row-1), S: down (row+1), E: right (col+1), W: left (col-1)
        dir_map = {'N': (-1, 0), 'S': (1, 0), 'E': (0, 1), 'W': (0, -1)}
        dx, dy = dir_map[self.direction]

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
        visible_pos = self.get_visible_positions()
        
        for pos in visible_pos:
            # Only record gold if it's in our provided view and equals 1
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
                # Helper receives ack from finder
                if self.role == 'helper' and self.state == "helper_waiting_ack":
                    helper_id = content.get("helper_id")
                    msg_index = content.get("index")
                    
                    if helper_id == self.id and msg_index == self.current_message_index:
                        # I was selected
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
                self.wait_timer = 0
                return "idle"
            
            return self._get_move_action_towards(deposit)
        
        # AT DEPOSIT 
        if self.state == "at_deposit":
            if not self.holding_gold:
            # Deposit succeeded or gold was dropped by simulation
                return "idle"
            
            # Timeout after waiting too long at deposit
            self.wait_timer += 1
            if self.wait_timer > 20:
                print(f"DEBUG: R{self.id} timed out at deposit (partner didn't arrive), resetting")
                self._reset_to_exploring()
                return "idle"
            
            return "idle"
        
        # READY TO PICKUP - execute pickup
        if self.state == "ready_to_pickup":
            # Transition to carrying_gold if pickup was successful
            if self.holding_gold:
                self.state = "carrying_gold"
                self.pickup_timer = 0
                return "idle"
            
            # Timeout if stuck 
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
    
    def update(self, visible_cells: Dict[Tuple[int, int], int], physical_holding_gold: bool = False):
        """Main update loop: observe, process messages, decide, execute"""
        self.observe(visible_cells)
        self._sense_physical_gold_state(physical_holding_gold)
        self.process_messages()
        action = self.decide_action(visible_cells)
        self.next_action = action
        self._broadcast_my_state()

    def _sense_physical_gold_state(self, physical_holding_gold: bool):
        """
        Sense the physical state of gold carrying and update internal state accordingly.
        This simulates proprioceptive sensing - the robot can feel whether it's actually carrying gold.
        """
        # Detect successful pickup
        if physical_holding_gold and not self.holding_gold:
            # Physics says we picked up gold, update belief
            self.holding_gold = True
            print(f"DEBUG: R{self.id} sensed successful pickup")
        
        # Detect gold drop or successful deposit
        elif not physical_holding_gold and self.holding_gold:
            
            if self.state == "at_deposit":
                # We were at deposit and gold disappeared - successful deposit!
                print(f"DEBUG: R{self.id} sensed successful deposit")
                self.holding_gold = False
                self.carrying_with = None
                self.target_gold_pos = None
                self._reset_to_exploring()
            else:
                # Gold was dropped (partners separated)
                print(f"DEBUG: R{self.id} sensed gold drop (partners separated)")
                self.holding_gold = False
                self.carrying_with = None
                self.target_gold_pos = None
                self._reset_to_exploring()
    
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
