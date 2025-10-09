import random
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

from utils import Direction

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
        self.paxos_role = 'follower'  # follower, leader
        self.paxos_state = 'idle'  # idle, preparing, proposing, finished
        self.promises_received = set()
        self.accepts_received = set()
        self.current_plan = None

        # State-related timers
        self.wait_timer = 0

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
            msg_type = msg.get("type")
            sender_id = msg.get("sender_id")
            content = msg.get("content", {})

            if msg_type == "paxos_prepare":
                proposal_id = content.get("proposal_id")
                if proposal_id >= self.highest_proposal_seen:
                    self.highest_proposal_seen = proposal_id
                    self.paxos_state = 'preparing' # Show we are engaged in a paxos round
                    # Promise not to accept proposals with a lower number
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
                if self.paxos_role == 'leader' and self.paxos_state == 'preparing':
                    proposal_id = content.get("proposal_id")
                    # Check if the promise is for the current proposal
                    if proposal_id == self.highest_proposal_seen:
                        self.promises_received.add(sender_id)

                        # If a promise contains a previously accepted value, we must use it
                        if content.get("accepted_proposal", -1) > self.accepted_proposal:
                            self.accepted_proposal = content["accepted_proposal"]
                            self.accepted_value = content["accepted_value"]
                        
                        # Check for majority
                        num_teammates = sum(1 for r in all_robots if r.group == self.group)
                        if len(self.promises_received) > num_teammates / 2:
                            self.paxos_state = 'proposing'
                            # Send ACCEPT message to all teammates
                            for robot in all_robots:
                                if robot.group == self.group:
                                    self.message_outbox.append({
                                        "type": "paxos_accept",
                                        "sender_id": self.id,
                                        "recipient_id": robot.id,
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
                    self.paxos_state = 'proposing' # Engaged in this proposal
                    self.message_outbox.append({
                        "type": "paxos_accepted",
                        "sender_id": self.id,
                        "recipient_id": sender_id,
                        "content": {"proposal_id": proposal_id}
                    })

            elif msg_type == "paxos_accepted":
                if self.paxos_role == 'leader' and self.paxos_state == 'proposing':
                    proposal_id = content.get("proposal_id")
                    if proposal_id == self.highest_proposal_seen:
                        self.accepts_received.add(sender_id)
                        
                        num_teammates = sum(1 for r in all_robots if r.group == self.group)
                        if len(self.accepts_received) > num_teammates / 2:
                            # PLAN IS COMMITTED
                            self.paxos_state = 'finished'
                            self.current_plan = self.accepted_value
                            
                            # Broadcast commit message
                            for robot in all_robots:
                                if robot.group == self.group:
                                    self.message_outbox.append({
                                        "type": "paxos_commit",
                                        "sender_id": self.id,
                                        "recipient_id": robot.id,
                                        "content": {"plan": self.current_plan}
                                    })
                            
                            # Reset for next round
                            self.paxos_role = 'follower'
                            self.promises_received = set()
                            self.accepts_received = set()

            elif msg_type == "paxos_commit":
                self.current_plan = content.get("plan")
                self.paxos_state = 'idle' # Ready for plan execution or next round
                # The logic in decide_action will now pick up this plan
            
            elif msg_type == "at_gold":
                # Partner has reached the gold
                if sender_id == self.carrying_with:
                    if self.position == self.target_gold_pos:
                        self.state = "ready_to_pickup"
            
            elif msg_type == "ready_pickup":
                # Partner is ready to pickup
                if sender_id == self.carrying_with:
                    if self.position == self.target_gold_pos and self.position == tuple(content["pos"]):
                        self.state = "ready_to_pickup"
            
            elif msg_type == "drop_gold":
                # Partner dropped the gold (moved wrong direction)
                if sender_id == self.carrying_with:
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
            # Unconditionally attempt to pickup. The simulation's rules will
            # verify that the partner is also present and ready.
            # This avoids state-checking race conditions between robots.
            return "pickup"
        
        # STATE: waiting_at_gold - At gold position, waiting for partner
        if self.state == "waiting_at_gold":
            self.wait_timer += 1

            # Check if we're actually at the target gold position
            if self.position != self.target_gold_pos:
                # Not at target yet, keep moving
                self.state = "moving_to_gold"
                self.wait_timer = 0
                return self._get_move_action_towards(self.target_gold_pos)
            
            # Check if partner has arrived
            partner = self._get_partner(all_robots)
            if partner and partner.position == self.position:
                # Partner arrived! Transition to ready
                self.state = "ready_to_pickup"
                self.wait_timer = 0
                # Notify partner we're ready
                self.message_outbox.append({
                    "type": "ready_pickup",
                    "sender_id": self.id,
                    "recipient_id": self.carrying_with,
                    "content": {"pos": self.position}
                })
                return "idle"
            
            # Check if gold still there
            if not grid_state[self.target_gold_pos] > 0:
                # Gold gone, reset
                print(f"DEBUG: R{self.id} gold at {self.target_gold_pos} disappeared, resetting")
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
                self.paxos_state = 'idle'
                self.wait_timer = 0
                return "idle"

            # Check for timeout
            if self.wait_timer > 20:
                print(f"DEBUG: R{self.id} timed out waiting for partner at {self.target_gold_pos}, resetting.")
                # Give up and go back to idle
                self.state = "idle"
                self.carrying_with = None
                self.target_gold_pos = None
                self.paxos_state = 'idle'
                self.wait_timer = 0
                return "idle"
            
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
        
        # STATE: idle - Search for gold or participate in Paxos
        if self.state == "idle":
            # Part 1: Check if we have a committed plan to execute
            if self.current_plan and self.id in self.current_plan:
                assignment = self.current_plan[self.id]
                self.state = "moving_to_gold"
                self.target_gold_pos = assignment["gold_pos"]
                self.carrying_with = assignment["partner_id"]
                self.paxos_state = 'idle' # Reset for next round
                self.current_plan = None  # Consume the plan
                return self._get_move_action_towards(self.target_gold_pos)

            # Part 2: Leader Election and Proposal
            idle_teammates = [r for r in all_robots if r.group == self.group and r.state == 'idle' and r.paxos_state == 'idle']
            if not idle_teammates:
                return "idle" # No one is available to form a plan

            leader = min(idle_teammates, key=lambda r: r.id)

            if self.id == leader.id and self.observed_gold:
                # I am the leader and I see gold, let's make a smarter plan.
                self.paxos_role = 'leader'
                self.paxos_state = 'preparing'

                # --- Smarter Plan Creation ---
                available_robots = list(idle_teammates)
                available_gold = set(self.observed_gold)
                plan = {}

                while len(available_robots) >= 2 and available_gold:
                    # Create a pair
                    robot1 = available_robots.pop(0)
                    robot2 = available_robots.pop(0)
                    
                    # Find the closest available gold for this pair and assign it
                    # (based on robot1's position for simplicity)
                    target_gold = min(available_gold, 
                                      key=lambda g: abs(g[0]-robot1.position[0]) + abs(g[1]-robot1.position[1]))
                    available_gold.remove(target_gold)

                    # Add the assignment for both robots to the plan
                    plan[robot1.id] = {"partner_id": robot2.id, "gold_pos": target_gold}
                    plan[robot2.id] = {"partner_id": robot1.id, "gold_pos": target_gold}
                # --- End of Smarter Plan Creation ---

                if plan:
                    proposal_id = self.get_next_proposal_number()
                    self.highest_proposal_seen = proposal_id
                    self.accepted_value = plan # Tentatively accept our own plan

                    # Send PREPARE message to all teammates
                    for robot in all_robots:
                        if robot.group == self.group and robot.id != self.id:
                            self.message_outbox.append({
                                "type": "paxos_prepare",
                                "sender_id": self.id,
                                "recipient_id": robot.id,
                                "content": {"proposal_id": proposal_id}
                            })
                    self.promises_received = {self.id} # We implicitly promise ourselves
                
                return "idle" # Wait for promises

            # Part 3: Default behavior if not leading or no plan
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
