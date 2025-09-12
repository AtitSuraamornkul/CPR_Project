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

def turn(robot, direction):
    dirs = ['N','E','S','W']
    idx = dirs.index(robot.direction)
    if direction == 'left':
        robot.direction = dirs[(idx-1) % 4]
    elif direction == 'right':
        robot.direction = dirs[(idx+1) % 4]

def pick_up(robots, grid):
    if not robots:
        return

    x, y = robots[0].position
    gold_on_pos = grid[x, y]
    
    # Separate robots by group
    group1_robots = [r for r in robots if r.group == 1]
    group2_robots = [r for r in robots if r.group == 2]

    g1_wants_pickup = len(group1_robots)
    g2_wants_pickup = len(group2_robots)

    g1_can_pickup = g1_wants_pickup == 2
    g2_can_pickup = g2_wants_pickup == 2

    if g1_can_pickup and g2_can_pickup:
        if gold_on_pos >= 2:
            # Both groups pick up gold
            for r in group1_robots:
                r.holding_gold = True
                r.carrying_with = group1_robots[1].id if r.id == group1_robots[0].id else group1_robots[0].id
            grid[x, y] -= 1
            
            for r in group2_robots:
                r.holding_gold = True
                r.carrying_with = group2_robots[1].id if r.id == group2_robots[0].id else group2_robots[0].id
            grid[x, y] -= 1
            
    elif g1_can_pickup and not g2_can_pickup:
        if gold_on_pos >= 1:
            # Group 1 picks up gold
            for r in group1_robots:
                r.holding_gold = True
                r.carrying_with = group1_robots[1].id if r.id == group1_robots[0].id else group1_robots[0].id
            grid[x, y] -= 1

    elif not g1_can_pickup and g2_can_pickup:
        if gold_on_pos >= 1:
            # Group 2 picks up gold
            for r in group2_robots:
                r.holding_gold = True
                r.carrying_with = group2_robots[1].id if r.id == group2_robots[0].id else group2_robots[0].id
            grid[x, y] -= 1

def move_with_gold(robot, grid_size, all_robots):
    """Handle movement when robot is carrying gold"""
    if not robot.holding_gold or robot.carrying_with is None:
        return False
    
    # Find the robot carrying gold together
    partner = next((r for r in all_robots if r.id == robot.carrying_with), None)
    if not partner or not partner.holding_gold:
        # Partner is not carrying gold anymore, drop gold
        robot.holding_gold = False
        robot.carrying_with = None
        return False
    
    # Check if both robots are at the same position
    if robot.position != partner.position:
        # Robots separated, drop gold
        robot.holding_gold = False
        robot.carrying_with = None
        partner.holding_gold = False
        partner.carrying_with = None
        return False
    
    # Both robots move together
    old_pos = robot.position
    move(robot, grid_size)
    move(partner, grid_size)
    
    # Check if they're still together after moving
    if robot.position != partner.position:
        # They separated during movement, drop gold
        robot.holding_gold = False
        robot.carrying_with = None
        partner.holding_gold = False
        partner.carrying_with = None
        return False
    
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