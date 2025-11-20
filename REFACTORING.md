# Code Refactoring Documentation

## Overview
The original `full.py` (874 lines) has been refactored into a modular structure for better organization and maintainability.

## New File Structure

```
CPR_Project/
├── utils.py           # Utility functions and enums
├── grid.py            # Grid class
├── robot.py           # Robot class (Finder-Helper protocol)
├── simulation.py      # Simulation class
├── main.py            # Entry point
├── run_statistics.py  # Statistics collection script (updated imports)
└── full.py            # Original file (can be kept for reference)
```

## File Descriptions

### `utils.py` (18 lines)
Contains utility functions and enums used across the project.
- `strip_ansi(text)` - Remove ANSI color codes from text
- `Direction` enum - Direction constants (NORTH, SOUTH, EAST, WEST)

### `grid.py` (39 lines)
Manages the simulation environment.
- `Grid` class - Handles the game board, gold placement, and deposit locations

### `robot.py` (545 lines)
Implements the robot agent and Finder-Helper protocol.
- `Robot` class - Complete robot logic including:
  - State machine (exploring, finder/helper states, carrying gold, etc.)
  - Message processing (found, response, ack, here, ack2)
  - Decision making and pathfinding
  - Vision system
  - Timeout mechanisms

### `simulation.py` (307 lines)
Orchestrates the simulation execution.
- `Simulation` class - Main game loop including:
  - Message delay system
  - Action execution
  - Collision detection
  - Scoring logic
  - Grid visualization

### `main.py` (39 lines)
Entry point for running the simulation.
- `main()` function - Initializes grid, robots, and runs simulation
- Can be executed directly: `python3 main.py`

## Usage

### Running the Simulation
```bash
python3 main.py
```

### Running Statistics Collection
```bash
python3 run_statistics.py 20    # Run 20 simulations
```

### Importing Modules
```python
from grid import Grid
from robot import Robot
from simulation import Simulation
from utils import strip_ansi, Direction

# Create a custom simulation
grid = Grid(size=20, num_gold=10)
# ... initialize robots ...
sim = Simulation(grid, group1, group2, steps=1000)
sim.run()
```

## Key Benefits

1. **Modularity**: Each file has a single, clear responsibility
2. **Maintainability**: Easier to locate and modify specific functionality
3. **Reusability**: Components can be imported independently
4. **Testing**: Individual modules can be tested in isolation
5. **Readability**: Smaller files are easier to understand

## Backward Compatibility

- The original `full.py` remains unchanged
- `run_statistics.py` has been updated to use the new modular imports
- All functionality remains identical to the original implementation

## Migration Notes

If you have other scripts importing from `full.py`, update them:
```python
# Old:
from full import Grid, Robot, Simulation

# New:
from grid import Grid
from robot import Robot
from simulation import Simulation
```
