import time
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Set, List, Optional

class Color:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

class PlaceType(Enum):
    MAIN_STATE = "main_state"
    CONDITION = "condition"
    RESOURCE = "resource"

@dataclass
class Place:
    name: str
    tokens: int = 0
    type: PlaceType = PlaceType.MAIN_STATE
    capacity: int = 1
    
    def __str__(self):
        color = Color.GREEN if self.type == PlaceType.MAIN_STATE else Color.BLUE
        return f"{color}{self.name}[{self.tokens}]{Color.RESET}"

@dataclass
class Transition:
    name: str
    input_places: Dict[str, int]  # place_name -> required_tokens
    output_places: Dict[str, int] # place_name -> produced_tokens
    
    def __str__(self):
        return f"{Color.YELLOW}{self.name}{Color.RESET}"

class PetriNet:
    def __init__(self):
        self.places: Dict[str, Place] = {}
        self.transitions: Dict[str, Transition] = {}
        self.history: List[str] = []
        
    def add_place(self, name: str, place_type: PlaceType = PlaceType.MAIN_STATE, initial_tokens: int = 0):
        self.places[name] = Place(name, initial_tokens, place_type)
    
    def add_transition(self, name: str, inputs: Dict[str, int], outputs: Dict[str, int]):
        self.transitions[name] = Transition(name, inputs, outputs)
    
    def is_enabled(self, transition_name: str) -> bool:
        """Check if a transition can fire"""
        transition = self.transitions[transition_name]
        
        # Check all input places have enough tokens
        for place_name, required_tokens in transition.input_places.items():
            if self.places[place_name].tokens < required_tokens:
                return False
        return True
    
    def fire_transition(self, transition_name: str) -> bool:
        """Fire a transition if enabled"""
        if not self.is_enabled(transition_name):
            return False
            
        transition = self.transitions[transition_name]
        
        # Remove tokens from input places
        for place_name, required_tokens in transition.input_places.items():
            self.places[place_name].tokens -= required_tokens
        
        # Add tokens to output places
        for place_name, produced_tokens in transition.output_places.items():
            self.places[place_name].tokens += produced_tokens
            
        self.history.append(f"Fired: {transition_name}")
        return True
    
    def get_current_state(self) -> str:
        """Get current main state (the one with token)"""
        for place in self.places.values():
            if place.type == PlaceType.MAIN_STATE and place.tokens > 0:
                return place.name
        return "unknown"
    
    def visualize(self):
        """Visualize the current state of the Petri net"""
        print("\n" + "="*60)
        print("PETRI NET STATE VISUALIZATION")
        print("="*60)
        
        # Show main states
        print(f"\n{Color.GREEN}MAIN STATES:{Color.RESET}")
        main_states = [p for p in self.places.values() if p.type == PlaceType.MAIN_STATE]
        for place in main_states:
            marker = " ◉ " if place.tokens > 0 else " ○ "
            print(f"  {marker} {place}")
        
        # Show conditions
        print(f"\n{Color.BLUE}CONDITIONS:{Color.RESET}")
        conditions = [p for p in self.places.values() if p.type == PlaceType.CONDITION]
        for place in conditions:
            if place.tokens > 0:
                print(f"  ✓ {place}")
        
        # Show enabled transitions
        print(f"\n{Color.YELLOW}ENABLED TRANSITIONS:{Color.RESET}")
        enabled = [t for t in self.transitions.values() if self.is_enabled(t.name)]
        for transition in enabled:
            print(f"  → {transition}")
        
        print(f"\nCurrent State: {Color.GREEN}{self.get_current_state()}{Color.RESET}")
        print("="*60)

def create_robot_petri_net() -> PetriNet:
    """Create the complete robot state machine Petri net"""
    net = PetriNet()
    
    # Add MAIN STATE places (GREEN)
    net.add_place("P_idle", PlaceType.MAIN_STATE, initial_tokens=1)
    net.add_place("P_moving_to_gold", PlaceType.MAIN_STATE)
    net.add_place("P_waiting_at_gold", PlaceType.MAIN_STATE)
    net.add_place("P_ready_to_pickup", PlaceType.MAIN_STATE)
    net.add_place("P_carrying_gold", PlaceType.MAIN_STATE)
    net.add_place("P_at_deposit", PlaceType.MAIN_STATE)
    
    # Add CONDITION places (BLUE)
    net.add_place("P_gold_observed", PlaceType.CONDITION)
    net.add_place("P_paxos_active", PlaceType.CONDITION)
    net.add_place("P_target_assigned", PlaceType.CONDITION)
    net.add_place("P_partner_assigned", PlaceType.CONDITION)
    net.add_place("P_gold_available", PlaceType.CONDITION, initial_tokens=1)
    net.add_place("P_at_gold_position", PlaceType.CONDITION)
    net.add_place("P_partner_at_gold", PlaceType.CONDITION)
    net.add_place("P_holding_gold", PlaceType.CONDITION)
    net.add_place("P_at_deposit_position", PlaceType.CONDITION)
    net.add_place("P_partner_at_deposit", PlaceType.CONDITION)
    net.add_place("P_score", PlaceType.CONDITION)
    
    # Add TRANSITIONS (YELLOW)
    transitions = [
        # Observe gold and start process
        ("T_observe_gold", 
         {"P_idle": 1}, 
         {"P_gold_observed": 1}),
        
        # Initiate Paxos consensus
        ("T_initiate_paxos", 
         {"P_gold_observed": 1}, 
         {"P_paxos_active": 1}),
        
        # Paxos succeeds - assign target and partner
        ("T_paxos_success", 
         {"P_paxos_active": 1}, 
         {"P_target_assigned": 1, "P_partner_assigned": 1}),
        
        # Start moving to gold
        ("T_start_moving", 
         {"P_target_assigned": 1}, 
         {"P_moving_to_gold": 1}),
        
        # Reach gold position
        ("T_reach_gold", 
         {"P_moving_to_gold": 1, "P_at_gold_position": 1}, 
         {"P_waiting_at_gold": 1}),
        
        # Partner arrives at gold
        ("T_partner_arrives", 
         {"P_waiting_at_gold": 1, "P_partner_at_gold": 1}, 
         {"P_ready_to_pickup": 1}),
        
        # Pickup gold
        ("T_pickup_gold", 
         {"P_ready_to_pickup": 1, "P_gold_available": 1}, 
         {"P_carrying_gold": 1, "P_holding_gold": 1}),
        
        # Start carrying to deposit
        ("T_start_carrying", 
         {"P_carrying_gold": 1}, 
         {"P_at_deposit": 1}),
        
        # Reach deposit position
        ("T_reach_deposit", 
         {"P_at_deposit": 1, "P_at_deposit_position": 1}, 
         {"P_at_deposit": 0, "P_holding_gold": 0}),  # Note: keeps P_at_deposit token
        
        # Partner reaches deposit
        ("T_partner_reaches_deposit", 
         {"P_at_deposit": 1, "P_partner_at_deposit": 1}, 
         {"P_at_deposit": 0}),
        
        # Deposit gold successfully
        ("T_deposit_gold", 
         {"P_at_deposit": 1, "P_partner_at_deposit": 1, "P_holding_gold": 1}, 
         {"P_idle": 1, "P_score": 1, "P_holding_gold": 0}),
        
        # Gold disappears while waiting
        ("T_gold_disappears", 
         {"P_waiting_at_gold": 1}, 
         {"P_idle": 1}),
        
        # Timeout while waiting
        ("T_timeout_waiting", 
         {"P_waiting_at_gold": 1}, 
         {"P_idle": 1}),
    ]
    
    for name, inputs, outputs in transitions:
        net.add_transition(name, inputs, outputs)
    
    return net

def simulate_robot_scenario():
    """Simulate a complete robot gold collection scenario"""
    net = create_robot_petri_net()
    
    print("🤖 ROBOT GOLD COLLECTION SIMULATION")
    print("Starting simulation...\n")
    
    # Initial state
    net.visualize()
    time.sleep(1)
    
    # Step 1: Observe gold
    print("\n>>> Step 1: Robot observes gold")
    net.fire_transition("T_observe_gold")
    net.visualize()
    time.sleep(1)
    
    # Step 2: Initiate Paxos
    print("\n>>> Step 2: Initiate Paxos consensus")
    net.fire_transition("T_initiate_paxos")
    net.visualize()
    time.sleep(1)
    
    # Step 3: Paxos succeeds
    print("\n>>> Step 3: Paxos succeeds - target assigned")
    net.fire_transition("T_paxos_success")
    net.visualize()
    time.sleep(1)
    
    # Step 4: Start moving to gold
    print("\n>>> Step 4: Start moving to gold")
    net.fire_transition("T_start_moving")
    net.visualize()
    time.sleep(1)
    
    # Step 5: Simulate reaching gold position
    print("\n>>> Step 5: Reached gold position")
    net.places["P_at_gold_position"].tokens = 1
    net.fire_transition("T_reach_gold")
    net.visualize()
    time.sleep(1)
    
    # Step 6: Partner arrives
    print("\n>>> Step 6: Partner robot arrives")
    net.places["P_partner_at_gold"].tokens = 1
    net.fire_transition("T_partner_arrives")
    net.visualize()
    time.sleep(1)
    
    # Step 7: Pickup gold
    print("\n>>> Step 7: Pickup gold with partner")
    net.fire_transition("T_pickup_gold")
    net.visualize()
    time.sleep(1)
    
    # Step 8: Start carrying to deposit
    print("\n>>> Step 8: Start carrying gold to deposit")
    net.fire_transition("T_start_carrying")
    net.visualize()
    time.sleep(1)
    
    # Step 9: Reach deposit position
    print("\n>>> Step 9: Reached deposit position")
    net.places["P_at_deposit_position"].tokens = 1
    net.fire_transition("T_reach_deposit")
    net.visualize()
    time.sleep(1)
    
    # Step 10: Partner reaches deposit
    print("\n>>> Step 10: Partner reaches deposit")
    net.places["P_partner_at_deposit"].tokens = 1
    net.fire_transition("T_partner_reaches_deposit")
    net.visualize()
    time.sleep(1)
    
    # Step 11: Deposit gold
    print("\n>>> Step 11: Deposit gold successfully!")
    net.fire_transition("T_deposit_gold")
    net.visualize()
    
    # Show final results
    print(f"\n🎉 SIMULATION COMPLETE!")
    print(f"Final score: {net.places['P_score'].tokens}")
    print(f"History: {net.history}")

def interactive_simulation():
    """Allow interactive firing of transitions"""
    net = create_robot_petri_net()
    
    print("🎮 INTERACTIVE PETRI NET SIMULATION")
    print("Type 'quit' to exit, 'help' for commands\n")
    
    while True:
        net.visualize()
        
        print("\nAvailable commands:")
        print("  'fire <transition>' - Fire a specific transition")
        print("  'add <place>' - Add token to a condition place")
        print("  'remove <place>' - Remove token from a place")
        print("  'list' - List all transitions and places")
        print("  'quit' - Exit simulation")
        
        command = input("\nEnter command: ").strip().lower()
        
        if command == 'quit':
            break
        elif command == 'help':
            print("\nAvailable transitions:", list(net.transitions.keys()))
            print("Available places:", list(net.places.keys()))
        elif command == 'list':
            print("\nTransitions:")
            for t in net.transitions:
                print(f"  {t}")
            print("\nPlaces:")
            for p_name, p in net.places.items():
                print(f"  {p}")
        elif command.startswith('fire '):
            transition = command[5:]
            if transition in net.transitions:
                if net.fire_transition(transition):
                    print(f"✅ Successfully fired {transition}")
                else:
                    print(f"❌ Cannot fire {transition} - not enabled")
            else:
                print(f"❌ Unknown transition: {transition}")
        elif command.startswith('add '):
            place = command[4:]
            if place in net.places:
                net.places[place].tokens += 1
                print(f"✅ Added token to {place}")
            else:
                print(f"❌ Unknown place: {place}")
        elif command.startswith('remove '):
            place = command[7:]
            if place in net.places and net.places[place].tokens > 0:
                net.places[place].tokens -= 1
                print(f"✅ Removed token from {place}")
            else:
                print(f"❌ Cannot remove token from {place}")
        else:
            print("❌ Unknown command")
        
        time.sleep(0.5)

if __name__ == "__main__":
    # Run automated simulation
    simulate_robot_scenario()
    
    print("\n" + "="*60)
    print("Would you like to try interactive mode? (y/n)")
    if input().strip().lower() == 'y':
        interactive_simulation()