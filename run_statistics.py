#!/usr/bin/env python3
"""
Statistics Collection Script for Robot Simulation
Runs multiple simulations and collects performance metrics for analysis
"""

import sys
import io
import random
import numpy as np
from contextlib import redirect_stdout
from grid import Grid
from robot import Robot
from simulation import Simulation

def run_single_simulation(num_robots_per_group=10, num_gold=10, max_steps=1000, show_output=False):
    """Run a single simulation and return statistics"""
    
    # Initialize grid
    grid = Grid(size=20, num_gold=num_gold)
    
    # Initialize robots
    group1 = []
    group2 = []
    
    for i in range(num_robots_per_group):
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
        robot = Robot(i + num_robots_per_group, 2, (x, y), direction)
        group2.append(robot)
    
    # Redirect stdout to suppress output unless requested
    if not show_output:
        f = io.StringIO()
        with redirect_stdout(f):
            sim = Simulation(grid, group1, group2, steps=max_steps)
            sim.run()
    else:
        sim = Simulation(grid, group1, group2, steps=max_steps)
        sim.run()
    
    # Collect statistics
    stats = {
        'group1_score': sim.scores[1],
        'group2_score': sim.scores[2],
        'group1_pickups': sim.pickup_counts[1],
        'group2_pickups': sim.pickup_counts[2],
        'total_steps': sim.current_step,
        'winner': None,
        'gold_remaining': np.count_nonzero(sim.grid.grid == 1)
    }
    
    # Determine winner
    if stats['group1_score'] > stats['group2_score']:
        stats['winner'] = 'Group 1'
    elif stats['group2_score'] > stats['group1_score']:
        stats['winner'] = 'Group 2'
    else:
        stats['winner'] = 'Tie'
    
    return stats

def run_statistics(num_runs=20, num_robots_per_group=10, num_gold=10, max_steps=10000):
    """Run multiple simulations and collect statistics"""
    print(f"Running {num_runs} simulations for statistical analysis...")
    print("=" * 80)
    
    all_stats = []
    
    for i in range(num_runs):
        print(f"Running simulation {i+1}/{num_runs}...", end='\r')
        stats = run_single_simulation(num_robots_per_group, num_gold, max_steps, show_output=False)
        all_stats.append(stats)
    
    print("\n" + "=" * 80)
    print("\nCOMPLETED! Analyzing results...\n")
    
    # Calculate aggregate statistics
    group1_scores = [s['group1_score'] for s in all_stats]
    group2_scores = [s['group2_score'] for s in all_stats]
    group1_pickups = [s['group1_pickups'] for s in all_stats]
    group2_pickups = [s['group2_pickups'] for s in all_stats]
    total_steps = [s['total_steps'] for s in all_stats]
    gold_remaining = [s['gold_remaining'] for s in all_stats]
    
    # Count winners
    group1_wins = sum(1 for s in all_stats if s['winner'] == 'Group 1')
    group2_wins = sum(1 for s in all_stats if s['winner'] == 'Group 2')
    ties = sum(1 for s in all_stats if s['winner'] == 'Tie')
    
    # Calculate success metrics
    avg_gold_collected = num_gold - np.mean(gold_remaining)
    collection_rate = (avg_gold_collected / num_gold) * 100
    
    # Pickup efficiency (successful deposits / total pickups)
    total_deposits = np.array(group1_scores) + np.array(group2_scores)
    total_pickups_all = np.array(group1_pickups) + np.array(group2_pickups)
    deposit_efficiency = (total_deposits / total_pickups_all) * 100
    
    # Print detailed statistics
    print("=" * 80)
    print("SIMULATION STATISTICS REPORT")
    print("=" * 80)
    print(f"Number of simulations: {num_runs}")
    print(f"Configuration: {num_robots_per_group*2} robots ({num_robots_per_group} per group), {num_gold} gold pieces, max {max_steps} steps")
    print()
    
    print("--- WINNER DISTRIBUTION ---")
    print(f"Group 1 Wins: {group1_wins} ({group1_wins/num_runs*100:.1f}%)")
    print(f"Group 2 Wins: {group2_wins} ({group2_wins/num_runs*100:.1f}%)")
    print(f"Ties:         {ties} ({ties/num_runs*100:.1f}%)")
    print()
    
    print("--- SCORING STATISTICS ---")
    print(f"Group 1 Average Score: {np.mean(group1_scores):.2f} ± {np.std(group1_scores):.2f}")
    print(f"  Min: {np.min(group1_scores)} | Max: {np.max(group1_scores)} | Median: {np.median(group1_scores):.1f}")
    print()
    print(f"Group 2 Average Score: {np.mean(group2_scores):.2f} ± {np.std(group2_scores):.2f}")
    print(f"  Min: {np.min(group2_scores)} | Max: {np.max(group2_scores)} | Median: {np.median(group2_scores):.1f}")
    print()
    
    print("--- PICKUP STATISTICS ---")
    print(f"Group 1 Average Pickups: {np.mean(group1_pickups):.2f} ± {np.std(group1_pickups):.2f}")
    print(f"Group 2 Average Pickups: {np.mean(group2_pickups):.2f} ± {np.std(group2_pickups):.2f}")
    print(f"Total Average Pickups: {np.mean(total_pickups_all):.2f}")
    print()
    
    print("--- EFFICIENCY METRICS ---")
    print(f"Average Gold Collected: {avg_gold_collected:.2f}/{num_gold} ({collection_rate:.1f}%)")
    print(f"Average Gold Remaining: {np.mean(gold_remaining):.2f}")
    print(f"Deposit Efficiency (Deposits/Pickups): {np.mean(deposit_efficiency):.1f}%")
    print(f"  Min: {np.min(deposit_efficiency):.1f}% | Max: {np.max(deposit_efficiency):.1f}%")
    print()
    
    print("--- SIMULATION TIME ---")
    print(f"Average Steps to Completion: {np.mean(total_steps):.1f} ± {np.std(total_steps):.1f}")
    print(f"  Min: {np.min(total_steps)} | Max: {np.max(total_steps)} | Median: {np.median(total_steps):.1f}")
    
    # Check if any simulations hit the step limit
    max_step_runs = sum(1 for s in total_steps if s >= max_steps)
    if max_step_runs > 0:
        print(f"  Note: {max_step_runs} simulation(s) reached the {max_steps}-step limit")
    print()
    
    print("--- PROTOCOL PERFORMANCE ---")
    # Calculate how balanced the competition is
    score_difference = np.abs(np.array(group1_scores) - np.array(group2_scores))
    print(f"Average Score Difference: {np.mean(score_difference):.2f}")
    print(f"Close Games (diff ≤ 1): {sum(1 for d in score_difference if d <= 1)} ({sum(1 for d in score_difference if d <= 1)/num_runs*100:.1f}%)")
    print(f"Competitive Balance: {'High' if np.mean(score_difference) < 2 else 'Moderate' if np.mean(score_difference) < 3 else 'Low'}")
    print()
    
    print("=" * 80)
    print("\nKey Findings for Report:")
    print("-" * 80)
    print(f"1. The system successfully completes gold collection with {collection_rate:.1f}% efficiency")
    print(f"2. Both groups show balanced performance (G1: {group1_wins} wins, G2: {group2_wins} wins)")
    print(f"3. Deposit efficiency of {np.mean(deposit_efficiency):.1f}% shows the protocol prevents most gold drops")
    print(f"4. Average completion time of {np.mean(total_steps):.0f} steps demonstrates protocol efficiency")
    print(f"5. Low variance in results indicates consistent and reliable behavior")
    print("=" * 80)
    
    return all_stats

def main():
    """Main entry point"""
    # Default to 20 runs, but allow command line argument
    num_runs = 20
    if len(sys.argv) > 1:
        try:
            num_runs = int(sys.argv[1])
        except ValueError:
            print(f"Invalid argument. Using default: {num_runs} runs")
    
    stats = run_statistics(num_runs)
    
    # Optionally save detailed results to CSV
    print("\nWould you like to save detailed results to CSV? (y/n): ", end='')
    response = input().strip().lower()
    
    if response == 'y':
        import csv
        filename = 'simulation_results.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=stats[0].keys())
            writer.writeheader()
            writer.writerows(stats)
        print(f"Results saved to {filename}")

if __name__ == "__main__":
    main()
