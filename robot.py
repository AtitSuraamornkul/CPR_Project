import random

class Robot:
    def __init__(self, rid, group, pos, grid_size, direction=None):
        self.id = rid
        self.group = group
        self.position = pos
        self.grid_size = grid_size
        self.direction = direction if direction else random.choice(['N','S','E','W'])
        self.holding_gold = False
        self.carrying_with = None
        self.message_inbox = []
        self.message_outbox = []
        self.known_gold_locations = {}
        self.target_gold_pos = None
        self.action = None
        self.state = "wandering"
        self.waiting_timer = 0
        self.accepted_proposal = None
        # For synchronized movement
        self.proposed_direction = None
        self.partner_direction = None


    def sense(self, grid):
        x, y = self.position
        positions = []

        if self.direction == 'N':
            positions = [(x-1,y-1),(x-1,y),(x-1,y+1),
                         (x-2,y-2),(x-2,y-1),(x-2,y),(x-2,y+1),(x-2,y+2)]
        elif self.direction == 'S':
            positions = [(x+1,y-1),(x+1,y),(x+1,y+1),
                         (x+2,y-2),(x+2,y-1),(x+2,y),(x+2,y+1),(x+2,y+2)]
        elif self.direction == 'E':
            positions = [(x-1,y+1),(x,y+1),(x+1,y+1),
                         (x-2,y+2),(x-1,y+2),(x,y+2),(x+1,y+2),(x+2,y+2)]
        elif self.direction == 'W':
            positions = [(x-1,y-1),(x,y-1),(x+1,y-1),
                         (x-2,y-2),(x-1,y-2),(x,y-2),(x+1,y-2),(x+2,y-2)]

        valid = [(i,j) for i,j in positions if 0 <= i < self.grid_size and 0 <= j < self.grid_size]
        sensed_data = [(i,j,grid[i,j]) for i,j in valid]

        for i, j, value in sensed_data:
            if value == 1 and (i,j) not in self.known_gold_locations:
                self.known_gold_locations[(i, j)] = "unknown"
                self.send_message("gold_location", {"pos": [i,j]}, broadcast=True)

    def update(self, grid, robots):
            self.action = None
            self._process_messages(robots)
            self.sense(grid)

            if self.state == "idle":
                self.state = "wandering"
                self.action = random.choice(['move', 'turn_left', 'turn_right'])

            if self.state == "wandering":
                unclaimed_gold = [pos for pos, status in self.known_gold_locations.items() if status == "unknown"]
                if unclaimed_gold:
                    self.target_gold_pos = unclaimed_gold[0]
                    self.state = "moving_to_gold"
                    self.known_gold_locations[self.target_gold_pos] = "claimed"
                    self.send_message("claim_gold", {"pos": self.target_gold_pos}, broadcast=True)
                else:
                    self.action = random.choice(['move', 'turn_left', 'turn_right'])

            elif self.state == "moving_to_gold":
                if self.position == self.target_gold_pos:
                    self.state = "at_gold"
                    robots_at_pos = [r for r in robots if r.position == self.position and r.id != self.id]
                    waiting_robots = [r for r in robots_at_pos if r.state == "waiting_for_partner"]
                    if waiting_robots:
                        partner = waiting_robots[0]
                        self.carrying_with = partner.id
                        partner.carrying_with = self.id
                        self.send_message("accept_pickup", {"pos": self.position}, recipient_id=partner.id)
                        self.state = "forming_pair"
                else:
                    self._move_towards(self.target_gold_pos)

            elif self.state == "at_gold":
                robots_at_pos = [r for r in robots if r.position == self.position and r.id != self.id]
                if robots_at_pos:
                    partner = robots_at_pos[0]
                    if partner.state in ["at_gold", "waiting_for_partner"]:
                        self.send_message("propose_pickup", {"pos": self.position}, recipient_id=partner.id)
                        self.state = "waiting_for_partner"
                        self.waiting_timer = 0
                else:
                    self.send_message("propose_pickup", {"pos": self.position}, broadcast=True, at_pos=self.position)
                    self.state = "waiting_for_partner"
                    self.waiting_timer = 0

            elif self.state == "waiting_for_partner":
                if self.carrying_with:
                    self.state = "forming_pair"
                elif self.waiting_timer > 15:
                    self.state = "wandering"
                    self.known_gold_locations[self.target_gold_pos] = "unknown"
                    self.send_message("abandon_pickup", {"pos": self.target_gold_pos}, broadcast=True)
                    self.target_gold_pos = None
                    self.accepted_proposal = None
                else:
                    self.waiting_timer += 1
            
            elif self.state == "forming_pair":
                if self.id < self.carrying_with:
                    self.send_message("confirm_pickup", {"partner_id": self.carrying_with, "pos": self.target_gold_pos}, recipient_id=self.carrying_with)
                    self.state = "carrying_gold"
                    self.holding_gold = True
                    self.send_message("gold_collected", {"pos": self.target_gold_pos}, broadcast=True)

            elif self.state == "carrying_gold":
                deposit_pos = (0, 0) if self.group == 1 else (self.grid_size-1, self.grid_size-1)
                if self.position == deposit_pos:
                    self.state = "at_deposit"
                else:
                    # ** BUG FIX AREA **
                    # Only propose a new move if not already waiting for partner's response
                    if not self.proposed_direction:
                        move_direction = self._get_move_direction(deposit_pos)
                        if move_direction:
                            self.proposed_direction = move_direction
                            self.send_message("propose_move", {"direction": self.proposed_direction}, recipient_id=self.carrying_with)

                    # Check for agreement if we have both proposals
                    if self.proposed_direction and self.partner_direction:
                        if self.proposed_direction == self.partner_direction:
                            # Agreement! Set action to move
                            if self.direction != self.proposed_direction:
                                self.action = self._get_turn_direction(self.direction, self.proposed_direction)
                            else:
                                self.action = 'move'
                        else:
                            # Disagreement, drop gold
                            self.send_message("drop_gold", {"pos": self.position}, broadcast=True)
                            self.holding_gold = False
                            self.carrying_with = None
                            self.state = "wandering"
                            self.proposed_direction = None
                            self.partner_direction = None

            elif self.state == "at_deposit":
                self.holding_gold = False
                self.carrying_with = None
                self.accepted_proposal = None
                self.state = "wandering"
                self.action = random.choice(['move', 'turn_left', 'turn_right'])

            self._execute_action(grid)

    def _execute_action(self, grid):
        if self.action:
            if self.action == 'move':
                self._move()
            elif self.action == 'turn_left':
                self._turn('left')
            elif self.action == 'turn_right':
                self._turn('right')
            
            # ** BUG FIX ** Reset proposals after a successful action
            if self.state == "carrying_gold":
                self.proposed_direction = None
                self.partner_direction = None


    def _move(self):
        x, y = self.position
        if self.direction == 'N' and x-1 >= 0:
            self.position = (x-1, y)
        elif self.direction == 'S' and x+1 < self.grid_size:
            self.position = (x+1, y)
        elif self.direction == 'E' and y+1 < self.grid_size:
            self.position = (x, y+1)
        elif self.direction == 'W' and y-1 >= 0:
            self.position = (x, y-1)

    def _turn(self, direction):
        dirs = ['N','E','S','W']
        idx = dirs.index(self.direction)
        if direction == 'left':
            self.direction = dirs[(idx-1) % 4]
        elif direction == 'right':
            self.direction = dirs[(idx+1) % 4]

    def _move_towards(self, target_pos):
        move_direction = self._get_move_direction(target_pos)
        if move_direction:
            if self.direction != move_direction:
                self.action = self._get_turn_direction(self.direction, move_direction)
            else:
                self.action = 'move'

    def _get_move_direction(self, target_pos):
        path = []
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]

        if dx > 0: path.extend(['S'] * dx)
        if dx < 0: path.extend(['N'] * -dx)
        if dy > 0: path.extend(['E'] * dy)
        if dy < 0: path.extend(['W'] * -dy)
        
        if path:
            return path[0]
        return None
        
    def _get_turn_direction(self, current_direction, target_direction):
        dirs = ['N', 'E', 'S', 'W']
        current_idx = dirs.index(current_direction)
        target_idx = dirs.index(target_direction)

        if current_idx == target_idx:
            return None

        if (current_idx + 1) % 4 == target_idx:
            return 'turn_right'
        else:
            return 'turn_left'

    def send_message(self, msg_type, content, broadcast=False, at_pos=None, recipient_id=None):
        msg = {"sender_id": self.id, "type": msg_type, "content": content}
        if broadcast:
            msg["broadcast"] = True
            if at_pos:
                msg["at_pos"] = at_pos
        if recipient_id is not None:
            msg["recipient_id"] = recipient_id
        self.message_outbox.append(msg)


    def _process_messages(self, robots):
        for msg in self.message_inbox:
            msg_type = msg["type"]
            content = msg["content"]
            sender_id = msg["sender_id"]

            if msg_type == "gold_location":
                pos = tuple(content["pos"])
                if pos not in self.known_gold_locations:
                    self.known_gold_locations[pos] = "unknown"

            elif msg_type == "claim_gold":
                pos = tuple(content["pos"])
                if pos in self.known_gold_locations:
                    self.known_gold_locations[pos] = "claimed"

            elif msg_type == "propose_pickup":
                pos = tuple(content["pos"])
                if self.position == pos and self.state in ["at_gold", "waiting_for_partner"]:
                    if not self.carrying_with:
                        self.send_message("accept_pickup", {"pos": pos}, recipient_id=sender_id)
                        self.carrying_with = sender_id
                        self.state = "forming_pair"

            elif msg_type == "accept_pickup":
                pos = tuple(content["pos"])
                if self.position == pos and not self.carrying_with:
                    self.carrying_with = sender_id
                    self.state = "forming_pair"

            elif msg_type == "confirm_pickup":
                self.carrying_with = sender_id
                self.target_gold_pos = tuple(content["pos"])
                self.state = "carrying_gold"
                self.holding_gold = True
                self.accepted_proposal = None
            
            elif msg_type == "abandon_pickup":
                pos = tuple(content["pos"])
                if self.accepted_proposal == sender_id:
                    self.accepted_proposal = None
                    if self.position == pos:
                        self.state = "at_gold"
                    else:
                        self.state = "wandering"
                elif self.target_gold_pos == pos and not self.holding_gold:
                    self.state = "wandering"
                    self.target_gold_pos = None

            elif msg_type == "gold_collected":
                pos = tuple(content["pos"])
                if pos in self.known_gold_locations:
                    self.known_gold_locations.pop(pos, None)
                    if self.target_gold_pos == pos and not self.holding_gold:
                        self.state = "wandering"
                        self.target_gold_pos = None
            
            elif msg_type == "propose_move":
                if self.carrying_with == sender_id:
                    self.partner_direction = content["direction"]
                    # If I'm not the leader, I reply with my move
                    if self.id > self.carrying_with and not self.proposed_direction:
                         deposit_pos = (0, 0) if self.group == 1 else (self.grid_size-1, self.grid_size-1)
                         move_direction = self._get_move_direction(deposit_pos)
                         self.proposed_direction = move_direction
                         self.send_message("propose_move", {"direction": self.proposed_direction}, recipient_id=self.carrying_with)


            elif msg_type == "drop_gold":
                pos = tuple(content["pos"])
                if self.carrying_with:
                    self.holding_gold = False
                    self.carrying_with = None
                    self.state = "wandering"
                    # ** BUG FIX ** Reset proposals on drop
                    self.proposed_direction = None
                    self.partner_direction = None
                    print(f"DEBUG: Robot {self.id} dropped gold at {pos}")


        self.message_inbox = []