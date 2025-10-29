"""
Test script to expose timing issues caused by message delays
"""
import sys
from full import *

def main():
    print("=" * 80)
    print("TESTING MESSAGE DELAYS - Looking for coordination failures")
    print("=" * 80)
    
    # Initialize grid with fewer gold to see faster results
    grid = Grid(size=20, num_gold=5)
    
    # Initialize robots
    group1 = []
    group2 = []
    
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
        robot = Robot(i + 10, 2, (x, y), direction)
        group2.append(robot)
    
    # Run simulation with delays
    print("\n🔥 MESSAGE DELAYS ENABLED: 1-5 step delays on all messages\n")
    sim = Simulation(grid, group1, group2, steps=200, message_delay_range=(1, 5))
    
    # Track issues
    step_count = 0
    max_pending = 0
    
    original_run = sim.run
    
    def tracked_run():
        try:
            original_run()
        except Exception as e:
            print(f"\n❌ EXCEPTION OCCURRED: {e}")
            import traceback
            traceback.print_exc()
    
    tracked_run()
    
    print("\n" + "=" * 80)
    print("POTENTIAL ISSUES TO OBSERVE:")
    print("=" * 80)
    print("1. ⏱️  STALE STATE: Robots make decisions based on old teammate positions")
    print("2. 🔄 RACE CONDITIONS: Multiple robots propose simultaneously, causing conflicts")
    print("3. 🤝 COORDINATION FAILURES: Partners don't arrive at gold at same time")
    print("4. 📦 STUCK IN PREPARING: Paxos promises arrive late, robots stuck waiting")
    print("5. 🎯 DOUBLE ASSIGNMENT: Same gold assigned to multiple pairs due to delays")
    print("6. 💔 PARTNER MISMATCH: Robot thinks it has partner, but partner moved on")
    print("=" * 80)

if __name__ == "__main__":
    main()
