from grid import Grid
from utils import create_group
from simulation import Simulation

if __name__ == "__main__":
    grid = Grid(size=20, num_gold=15)

    group1 = create_group(1, 3, grid.size)
    group2 = create_group(2, 3, grid.size)

    sim = Simulation(grid, group1, group2, steps=30)
    sim.run()