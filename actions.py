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

def pick_up(robot, robots, grid):
    same_group = [r for r in robots if r.group == robot.group]
    if len(same_group) == 2:
        x, y = robot.position
        if grid[x,y] >= 1:
            # Check if exactly 2 robots from same group are trying to pick up
            picking_up = [r for r in same_group if r.holding_gold == False]
            if len(picking_up) == 2:
                for r in picking_up: 
                    r.holding_gold = True
                    r.carrying_with = picking_up[1].id if r.id == picking_up[0].id else picking_up[0].id
                grid[x,y] -= 1

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