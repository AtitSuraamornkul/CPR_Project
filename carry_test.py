import time
from grid import Grid
from robot import Robot
from actions import pick_up, move_with_gold, check_deposit_delivery, move
from simulation import Simulation

def print_step(title, sim):
    print(f"\n=== {title} ===")
    sim._print_grid()
    print("Robots:", [(r.id, r.group, r.position, r.direction, r.holding_gold, r.carrying_with) for r in (sim.group1 + sim.group2)])
    time.sleep(1)

def main():
    # Setup: 5x5 grid, known gold and deposits
    g = Grid(size=5, num_gold=0)
    g.grid[:, :] = 0
    g.grid[0, 0] = 2   # Group 1 deposit (top-left)
    g.grid[4, 4] = 3   # Group 2 deposit (bottom-right)
    g.grid[2, 2] = 1   # Gold at (2,2) - visible initially

    # Two Group 1 robots at different positions so gold is visible
    r1 = Robot(rid=1, group=1, pos=(3, 3), direction='N')
    r2 = Robot(rid=2, group=1, pos=(3, 1), direction='N')

    sim = Simulation(g, group1=[r1, r2], group2=[], steps=0)

    print_step("Initial", sim)

    # Move both robots onto the gold at (2,2) so pickup is deterministic
    # Step 1: r1 moves North to (2,3); r2 moves East to (3,2)
    r1.direction = 'N'; move(r1, g.size)
    r2.direction = 'E'; move(r2, g.size)
    print_step("Move r1 N, r2 E", sim)

    # Step 2: r1 moves West to (2,2); r2 moves North to (2,2)
    r1.direction = 'W'; move(r1, g.size)
    r2.direction = 'N'; move(r2, g.size)
    print_step("Move r1 W to gold, r2 N to gold", sim)

    # Pick up (must be exactly two same-group robots on gold)
    robots_here = [r for r in (sim.group1 + sim.group2) if r.position == (2, 2)]
    pick_up(robots_here, g.grid)
    print_step("After pick_up", sim)

    # Move to deposit (0,0): North twice (x-1), then West twice (y-1)
    for k in range(2):
        r1.direction = 'N'
        r2.direction = 'N'
        move_with_gold(r1, g.size, sim.group1 + sim.group2)
        print_step(f"Move North step {k+1}", sim)

    for k in range(2):
        r1.direction = 'W'
        r2.direction = 'W'
        move_with_gold(r1, g.size, sim.group1 + sim.group2)
        print_step(f"Move West step {k+1}", sim)

    # Deliver
    scores = {1: 0, 2: 0}
    delivered = check_deposit_delivery(r1, g.size, scores, sim.group1 + sim.group2)
    print_step(f"Delivered={delivered}, Scores={scores}", sim)

if __name__ == "__main__":
    main()