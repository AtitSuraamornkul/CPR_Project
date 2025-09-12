def move(robot, grid_size):
    x, y = robot.position
    if robot.direction == 'N' and x-1 >= 0:
        robot.position = (x-1, y)
    elif robot.direction == 'S' and x+1 < grid_size:
        robot.position = (x+1, y)
    elif robot.direction == 'E' and y+1 < grid_size:
        robot.position = (x, y+1)
    elif robot.direction == 'W' and y-1 >= 0:
        robot.position = (x, y-1)

def get_turn_direction(current_direction, target_direction):
    dirs = ['N', 'E', 'S', 'W']
    current_idx = dirs.index(current_direction)
    target_idx = dirs.index(target_direction)

    if current_idx == target_idx:
        return None

    if (current_idx + 1) % 4 == target_idx:
        return 'turn_right'
    else:
        return 'turn_left'

def turn(robot, direction):
    dirs = ['N','E','S','W']
    idx = dirs.index(robot.direction)
    if direction == 'left':
        robot.direction = dirs[(idx-1) % 4]
    elif direction == 'right':
        robot.direction = dirs[(idx+1) % 4]

def pick_up(robots, grid):
    if not robots:
        return []

    x, y = robots[0].position
    gold_on_pos = grid[x, y]
    print(f"Attempting pickup at {x, y} with {len(robots)} robots.")
    
    # Separate robots by group and count them
    group1_robots = [r for r in robots if r.group == 1 and r.action == 'pick_up']
    group2_robots = [r for r in robots if r.group == 2 and r.action == 'pick_up']

    g1_wants_pickup = len(group1_robots)
    g2_wants_pickup = len(group2_robots)
    print(f"Group 1 wants pickup: {g1_wants_pickup}, Group 2 wants pickup: {g2_wants_pickup}")

    successful_pickups = []

    # Case 1: 2 robots from group 1, 2 from group 2
    if g1_wants_pickup == 2 and g2_wants_pickup == 2:
        if gold_on_pos >= 2:
            print("Both groups picking up gold.")
            # Both groups pick up gold
            r1, r2 = group1_robots[0], group1_robots[1]
            r1.carrying_with = r2.id
            r2.carrying_with = r1.id
            r1.holding_gold = True
            r2.holding_gold = True
            r1.waiting_for_partner = False
            r2.waiting_for_partner = False
            grid[x, y] -= 1
            successful_pickups.append(1)
            
            r3, r4 = group2_robots[0], group2_robots[1]
            r3.carrying_with = r4.id
            r4.carrying_with = r3.id
            r3.holding_gold = True
            r4.holding_gold = True
            r3.waiting_for_partner = False
            r4.waiting_for_partner = False
            grid[x, y] -= 1
            successful_pickups.append(2)

    # Case 2: Exactly 2 robots from one group
    elif g1_wants_pickup == 2 and g2_wants_pickup == 0:
        if gold_on_pos >= 1:
            print("Group 1 picking up gold.")
            # Group 1 picks up gold
            r1, r2 = group1_robots[0], group1_robots[1]
            r1.carrying_with = r2.id
            r2.carrying_with = r1.id
            r1.holding_gold = True
            r2.holding_gold = True
            r1.waiting_for_partner = False
            r2.waiting_for_partner = False
            grid[x, y] -= 1
            successful_pickups.append(1)

    elif g2_wants_pickup == 2 and g1_wants_pickup == 0:
        if gold_on_pos >= 1:
            print("Group 2 picking up gold.")
            # Group 2 picks up gold
            r1, r2 = group2_robots[0], group2_robots[1]
            r1.carrying_with = r2.id
            r2.carrying_with = r1.id
            r1.holding_gold = True
            r2.holding_gold = True
            r1.waiting_for_partner = False
            r2.waiting_for_partner = False
            grid[x, y] -= 1
            successful_pickups.append(2)

    return successful_pickups

def move_with_gold(robot, grid_size, all_robots, grid):
    """Handle movement when robot is carrying gold"""
    if not robot.holding_gold or robot.carrying_with is None:
        return False
    
    # Find the robot carrying gold together
    partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
    if not partner or not partner.holding_gold:
        # Partner is not carrying gold anymore, drop gold
        robot.holding_gold = False
        robot.carrying_with = None
        grid[robot.position] += 1 # Drop gold at the current position
        return False
    
    # Check if both robots are at the same position and have the same direction
    if robot.position != partner.position or robot.direction != partner.direction:
        # Robots separated or moving in different directions, drop gold
        robot.holding_gold = False
        robot.carrying_with = None
        partner.holding_gold = False
        partner.carrying_with = None
        grid[robot.position] += 1 # Drop gold at the current position
        return False
    
    # Both robots move together
    move(robot, grid_size)
    move(partner, grid_size)
    
    return True

def check_deposit_delivery(robot, grid_size, scores, all_robots):
    """Check if robot delivered gold to deposit point and award points"""
    if not robot.holding_gold or robot.carrying_with is None:
        return False
    
    x, y = robot.position
    
    # Check if at deposit point
    if (robot.group == 1 and x == 0 and y == 0) or (robot.group == 2 and x == grid_size-1 and y == grid_size-1):
        # Find partner
        partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
        if partner and partner.holding_gold:
            # Both robots delivered gold successfully
            scores[robot.group] += 1
            robot.holding_gold = False
            robot.carrying_with = None
            partner.holding_gold = False
            partner.carrying_with = None
            return True
    
    return False
