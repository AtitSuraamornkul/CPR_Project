
import unittest
from grid import Grid
from robot import Robot
from simulation import Simulation

class TestRobot(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(size=10, num_gold=0)
        self.robot = Robot(rid=1, group=1, pos=(5, 5), grid_size=10)

    def test_move_north(self):
        self.robot.direction = 'N'
        self.robot._move()
        self.assertEqual(self.robot.position, (4, 5))

    def test_move_south(self):
        self.robot.direction = 'S'
        self.robot._move()
        self.assertEqual(self.robot.position, (6, 5))

    def test_move_east(self):
        self.robot.direction = 'E'
        self.robot._move()
        self.assertEqual(self.robot.position, (5, 6))

    def test_move_west(self):
        self.robot.direction = 'W'
        self.robot._move()
        self.assertEqual(self.robot.position, (5, 4))

    def test_turn_left(self):
        self.robot.direction = 'N'
        self.robot._turn('left')
        self.assertEqual(self.robot.direction, 'W')

    def test_turn_right(self):
        self.robot.direction = 'N'
        self.robot._turn('right')
        self.assertEqual(self.robot.direction, 'E')

class TestSensing(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(size=10, num_gold=0)
        self.robot = Robot(rid=1, group=1, pos=(5, 5), grid_size=10)

    def test_sense_gold(self):
        self.grid.grid[4, 5] = 1
        self.robot.direction = 'N'
        self.robot.sense(self.grid.grid)
        self.assertIn((4, 5), self.robot.known_gold_locations)

class TestGoldPickup(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(size=10, num_gold=0)
        self.grid.grid[5, 6] = 1
        self.robot1 = Robot(rid=1, group=1, pos=(5, 5), grid_size=10)
        self.robot2 = Robot(rid=2, group=1, pos=(5, 7), grid_size=10)
        self.robots = [self.robot1, self.robot2]

    def test_propose_pickup(self):
        self.robot1.target_gold_pos = (5, 6)
        self.robot1.state = "moving_to_gold"
        self.robot1.update(self.grid.grid, self.robots)
        self.assertEqual(self.robot1.state, "moving_to_gold")
        self.robot1.position = (5, 6)
        self.robot1.update(self.grid.grid, self.robots)
        self.assertEqual(self.robot1.state, "at_gold")
        self.robot1.update(self.grid.grid, self.robots)
        self.assertEqual(self.robot1.state, "waiting_for_partner")
        self.assertIn({"sender_id": 1, "type": "propose_pickup", "content": {"pos": (5, 6)}, "broadcast": True, "at_pos": (5, 6)}, self.robot1.message_outbox)

class TestSynchronizedMovement(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(size=10, num_gold=0)
        self.robot1 = Robot(rid=1, group=1, pos=(5, 5), grid_size=10)
        self.robot2 = Robot(rid=2, group=1, pos=(5, 5), grid_size=10)
        self.robot1.carrying_with = 2
        self.robot2.carrying_with = 1
        self.robot1.state = "carrying_gold"
        self.robot2.state = "carrying_gold"
        self.robot1.holding_gold = True
        self.robot2.holding_gold = True
        self.robots = [self.robot1, self.robot2]
        self.sim = Simulation(self.grid, [self.robot1, self.robot2], [], steps=1)

    def test_move_agreement(self):
        self.robot1.direction = 'N'
        self.robot2.direction = 'N'
        self.robot1.update(self.grid.grid, self.robots)
        self.robot2.update(self.grid.grid, self.robots)
        
        self.sim._process_messages(self.robots)

        self.robot1.update(self.grid.grid, self.robots)
        self.robot2.update(self.grid.grid, self.robots)

        self.assertEqual(self.robot1.action, 'move')
        self.assertEqual(self.robot2.action, 'move')

class TestGoldDrop(unittest.TestCase):
    def setUp(self):
        self.grid = Grid(size=10, num_gold=0)
        self.grid.grid[5,5] = 0
        self.robot1 = Robot(rid=1, group=1, pos=(5, 5), grid_size=10)
        self.robot2 = Robot(rid=2, group=1, pos=(5, 5), grid_size=10)
        self.robot1.carrying_with = 2
        self.robot2.carrying_with = 1
        self.robot1.state = "carrying_gold"
        self.robot2.state = "carrying_gold"
        self.robot1.holding_gold = True
        self.robot2.holding_gold = True
        self.robots = [self.robot1, self.robot2]
        self.sim = Simulation(self.grid, [self.robot1, self.robot2], [], steps=1)

    def test_move_disagreement_and_drop(self):
        self.robot1.direction = 'N'
        self.robot2.direction = 'E'
        self.robot1.update(self.grid.grid, self.robots)
        self.robot2.update(self.grid.grid, self.robots)
        
        self.sim._process_messages(self.robots)

        self.robot1.update(self.grid.grid, self.robots)
        self.robot2.update(self.grid.grid, self.robots)

        print(f"Robot 1 outbox: {self.robot1.message_outbox}")
        print(f"Robot 2 outbox: {self.robot2.message_outbox}")

        print(f"Before processing drop: {self.grid.grid[5,5]}")
        self.sim._process_messages(self.robots)
        print(f"After processing drop: {self.grid.grid[5,5]}")

        self.assertEqual(self.grid.grid[5,5], 1)
        self.assertEqual(self.robot1.state, "wandering")
        self.assertEqual(self.robot2.state, "wandering")

if __name__ == "__main__":
    unittest.main()
