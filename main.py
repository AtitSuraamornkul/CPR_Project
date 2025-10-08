from grid import Grid
from utils import create_group
from simulation import Simulation

if __name__ == "__main__":
    grid = Grid(size=20, num_gold=15)

    group1 = create_group(1, 5, grid.size)
    group2 = create_group(2, 5, grid.size, start_id=10)

    sim = Simulation(grid, group1, group2, steps=5000)
    sim.run()