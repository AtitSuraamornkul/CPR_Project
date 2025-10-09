import random

from grid import Grid
from robot import Robot
from simulation import Simulation

def main():
    # Initialize grid
    grid = Grid(size=20, num_gold=10)
    
    # Initialize robots
    group1 = []
    group2 = []
    
    # Create 10 robots per group as per the README
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
        robot = Robot(i + 10, 2, (x, y), direction) # Use i+20 for unique IDs to be safe
        group2.append(robot)
    
    # Run simulation with a high step count as a safety cutoff
    sim = Simulation(grid, group1, group2, steps=2000)
    sim.run()

if __name__ == "__main__":
    main()
