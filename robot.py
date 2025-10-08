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
            else:
                self._move_towards(self.target_gold_pos)

        elif self.state == "at_gold":
            # Only the lowest ID robot at the location should propose
            is_lowest_id = True
            other_robots_at_pos = [r for r in robots if r.id != self.id and r.group == self.group and r.position == self.position and r.state in ["at_gold", "waiting_for_partner"]]
            for r in other_robots_at_pos:
                if r.id < self.id:
                    is_lowest_id = False
                    break
            
            if is_lowest_id:
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
                self._move_towards(deposit_pos)

        elif self.state == "at_deposit":
            self.holding_gold = False
            self.carrying_with = None
            self.state = "wandering"
            self.action = random.choice(['move', 'turn_left', 'turn_right'])

        self._execute_action(grid)

    def _execute_action(self, grid):
        if self.action == 'move':
            self._move()
        elif self.action == 'turn_left':
            self._turn('left')
        elif self.action == 'turn_right':
            self._turn('right')

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
        path = []
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]

        if dx > 0: path.extend(['S'] * dx)
        if dx < 0: path.extend(['N'] * -dx)
        if dy > 0: path.extend(['E'] * dy)
        if dy < 0: path.extend(['W'] * -dy)
        
        if path:
            next_move = path[0]
            if self.direction != next_move:
                turn_action = self._get_turn_direction(self.direction, next_move)
                if turn_action:
                    self.action = turn_action
            else:
                self.action = 'move'

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
                if self.state == "at_gold" and self.position == pos:
                    self.send_message("accept_pickup", {"pos": pos}, recipient_id=sender_id)
                    self.state = "waiting_for_partner"

            elif msg_type == "accept_pickup":
                pos = tuple(content["pos"])
                if self.state == "waiting_for_partner" and self.position == pos:
                    self.carrying_with = sender_id
                    self.state = "forming_pair"

            elif msg_type == "confirm_pickup":
                self.carrying_with = sender_id
                self.target_gold_pos = tuple(content["pos"])
                self.state = "carrying_gold"
                self.holding_gold = True
            
            elif msg_type == "abandon_pickup":
                pos = tuple(content["pos"])
                if self.target_gold_pos == pos:
                    self.state = "wandering"
                    self.target_gold_pos = None

            elif msg_type == "gold_collected":
                pos = tuple(content["pos"])
                if pos in self.known_gold_locations:
                    self.known_gold_locations.pop(pos, None)
                    if self.target_gold_pos == pos and not self.holding_gold:
                        self.state = "wandering"
                        self.target_gold_pos = None

        self.message_inbox = []