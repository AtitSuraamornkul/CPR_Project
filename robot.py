from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import random

@dataclass
class PaxosMessage:
    """Message for Paxos consensus protocol"""
    msg_type: str  # 'prepare', 'promise', 'accept', 'accepted'
    proposal_id: int
    sender_id: int
    value: Optional[any] = None
    accepted_id: Optional[int] = None
    accepted_value: Optional[any] = None

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
                if self.paxos_role == 'leader' and self.paxos_state == 'preparing':
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
                if self.paxos_role == 'leader' and self.paxos_state == 'proposing':
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
                            
                            self.paxos_role = 'follower'
                            self.promises_received = set()
                            self.accepts_received = set()

            elif msg_type == "paxos_commit":
                self.current_plan = content.get("plan")
                self.paxos_state = 'idle'
            
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
            if self.current_plan and self.id in self.current_plan:
                assignment = self.current_plan[self.id]
                self.state = "moving_to_gold"
                self.target_gold_pos = assignment["gold_pos"]
                self.carrying_with = assignment["partner_id"]
                self.paxos_state = 'idle'
                self.current_plan = None
                return self._get_move_action_towards(self.target_gold_pos)

            idle_teammate_ids = [r_id for r_id, r_state in self.teammate_states.items() if r_state.get("state") == 'idle' and r_state.get("paxos_state") == 'idle']
            all_idle_ids = idle_teammate_ids + [self.id] if self.paxos_state == 'idle' else idle_teammate_ids

            if not all_idle_ids:
                return "move"

            leader_id = min(all_idle_ids)

            if self.id == leader_id and self.observed_gold:
                self.paxos_role = 'leader'
                self.paxos_state = 'preparing'
                available_robot_ids = all_idle_ids
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
                        self.message_outbox.append({"type": "paxos_prepare", "sender_id": self.id, "recipient_id": teammate_id, "content": {"proposal_id": proposal_id}})
                    self.promises_received = {self.id}
                
                return "idle"

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
