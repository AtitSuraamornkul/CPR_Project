import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

def visualize_petri_net():
    # Create directed graph
    G = nx.DiGraph()
    
    # Define all places and transitions
    places = [
        # Core States
        'P_Idle', 'P_ExecutingPlan', 'P_WaitingAtGold', 
        'P_ReadyToPickup', 'P_CarryingGold', 'P_AtDeposit',
        # Knowledge & Communication
        'P_TeammateStateCache', 'P_MessageQueue', 'P_BroadcastOutbox', 'P_StepCounter',
        # Timing & Recovery
        'P_WaitTimer'
    ]
    
    transitions = [
        # Communication Layer
        'T_StateBroadcast', 'T_MessageDelivery', 'T_ProcessStateUpdate',
        # Coordination Workflow
        'T_PlanCommitted', 'T_ArriveAtGold', 'T_PartnerArrives', 
        'T_PickupGold', 'T_ReachDeposit', 'T_DepositGold',
        # Recovery & Failure
        'T_Timeout', 'T_GoldDisappears', 'T_PartnersSeparate',
        'T_StateExpired', 'T_MessageLoss'
    ]
    
    # Add nodes with types
    for place in places:
        G.add_node(place, node_type='place', shape='ellipse')
    for transition in transitions:
        G.add_node(transition, node_type='transition', shape='rectangle')
    
    # Define edges (Place → Transition → Place)
    edges = [
        # Communication Layer
        ('P_StepCounter', 'T_StateBroadcast'),
        ('T_StateBroadcast', 'P_BroadcastOutbox'),
        ('P_BroadcastOutbox', 'T_MessageDelivery'),
        ('T_MessageDelivery', 'P_MessageQueue'),
        ('P_MessageQueue', 'T_ProcessStateUpdate'),
        ('T_ProcessStateUpdate', 'P_TeammateStateCache'),
        
        # Coordination Workflow
        ('P_Idle', 'T_PlanCommitted'), ('P_TeammateStateCache', 'T_PlanCommitted'),
        ('T_PlanCommitted', 'P_ExecutingPlan'),
        ('P_ExecutingPlan', 'T_ArriveAtGold'),
        ('T_ArriveAtGold', 'P_WaitingAtGold'), ('T_ArriveAtGold', 'P_WaitTimer'),
        ('P_WaitingAtGold', 'T_PartnerArrives'), ('P_TeammateStateCache', 'T_PartnerArrives'),
        ('T_PartnerArrives', 'P_ReadyToPickup'),
        ('P_ReadyToPickup', 'T_PickupGold'),
        ('T_PickupGold', 'P_CarryingGold'),
        ('P_CarryingGold', 'T_ReachDeposit'),
        ('T_ReachDeposit', 'P_AtDeposit'),
        ('P_AtDeposit', 'T_DepositGold'),
        ('T_DepositGold', 'P_Idle'),
        
        # Recovery Transitions
        ('P_WaitingAtGold', 'T_Timeout'), ('P_WaitTimer', 'T_Timeout'),
        ('T_Timeout', 'P_Idle'),
        ('P_ExecutingPlan', 'T_GoldDisappears'),
        ('P_WaitingAtGold', 'T_GoldDisappears'),
        ('T_GoldDisappears', 'P_Idle'),
        ('P_CarryingGold', 'T_PartnersSeparate'),
        ('T_PartnersSeparate', 'P_Idle'),
        ('P_TeammateStateCache', 'T_StateExpired'),
        ('P_BroadcastOutbox', 'T_MessageLoss'),
        ('P_MessageQueue', 'T_MessageLoss')
    ]
    
    G.add_edges_from(edges)
    
    # Create hierarchical layout
    pos = {
        # Communication Layer (Top)
        'P_StepCounter': (0, 8),
        'T_StateBroadcast': (2, 8),
        'P_BroadcastOutbox': (4, 8),
        'T_MessageDelivery': (6, 8),
        'P_MessageQueue': (8, 8),
        'T_ProcessStateUpdate': (10, 8),
        'P_TeammateStateCache': (12, 8),
        
        # Coordination Layer (Middle)
        'P_Idle': (2, 5),
        'T_PlanCommitted': (4, 5),
        'P_ExecutingPlan': (6, 5),
        'T_ArriveAtGold': (8, 5),
        'P_WaitingAtGold': (10, 5),
        'T_PartnerArrives': (12, 5),
        'P_ReadyToPickup': (14, 5),
        'T_PickupGold': (16, 5),
        'P_CarryingGold': (18, 5),
        'T_ReachDeposit': (20, 5),
        'P_AtDeposit': (22, 5),
        'T_DepositGold': (24, 5),
        
        # Recovery Layer (Bottom)
        'P_WaitTimer': (10, 2),
        'T_Timeout': (8, 2),
        'T_GoldDisappears': (6, 2),
        'T_PartnersSeparate': (18, 2),
        'T_StateExpired': (12, 2),
        'T_MessageLoss': (4, 2)
    }
    
    # Create visualization
    plt.figure(figsize=(20, 10))
    
    # Draw places as ellipses
    place_nodes = [node for node in G.nodes if G.nodes[node]['node_type'] == 'place']
    nx.draw_networkx_nodes(G, pos, nodelist=place_nodes, 
                          node_shape='o', node_size=3000, 
                          node_color='lightblue', alpha=0.8, edgecolors='darkblue')
    
    # Draw transitions as rectangles
    transition_nodes = [node for node in G.nodes if G.nodes[node]['node_type'] == 'transition']
    nx.draw_networkx_nodes(G, pos, nodelist=transition_nodes, 
                          node_shape='s', node_size=2000, 
                          node_color='lightcoral', alpha=0.8, edgecolors='darkred')
    
    # Draw edges with different styles
    coordination_edges = [edge for edge in edges if any(p in ['P_Idle', 'P_ExecutingPlan', 'P_WaitingAtGold', 
                                                             'P_ReadyToPickup', 'P_CarryingGold', 'P_AtDeposit'] for p in edge)]
    communication_edges = [edge for edge in edges if any(p in ['P_TeammateStateCache', 'P_MessageQueue', 
                                                              'P_BroadcastOutbox', 'P_StepCounter'] for p in edge)]
    recovery_edges = [edge for edge in edges if any(p in ['P_WaitTimer'] for p in edge) or 
                     any(t in ['T_Timeout', 'T_GoldDisappears', 'T_PartnersSeparate', 
                              'T_StateExpired', 'T_MessageLoss'] for t in edge)]
    
    nx.draw_networkx_edges(G, pos, edgelist=coordination_edges, edge_color='blue', 
                          arrows=True, arrowsize=20, arrowstyle='->', width=2)
    nx.draw_networkx_edges(G, pos, edgelist=communication_edges, edge_color='green', 
                          arrows=True, arrowsize=20, arrowstyle='->', width=2)
    nx.draw_networkx_edges(G, pos, edgelist=recovery_edges, edge_color='red', 
                          arrows=True, arrowsize=20, arrowstyle='->', width=2, style='dashed')
    
    # Draw labels
    labels = {node: node for node in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
    
    # Add layer labels
    plt.text(-2, 8, 'COMMUNICATION\nLAYER', fontsize=12, fontweight='bold', 
             ha='center', va='center', bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen'))
    plt.text(-2, 5, 'COORDINATION\nLAYER', fontsize=12, fontweight='bold', 
             ha='center', va='center', bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue'))
    plt.text(-2, 2, 'RECOVERY\nLAYER', fontsize=12, fontweight='bold', 
             ha='center', va='center', bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral'))
    
    plt.title("Petri Net: Robot Coordination with Broadcast System\n(Latest Version)", size=16, pad=20)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def create_simplified_flow_diagram():
    """Create a simplified flow diagram showing the main coordination path"""
    fig, ax = plt.subplots(1, 1, figsize=(15, 8))
    
    # Define the main flow steps
    steps = [
        "IDLE\n(Broadcasting State)",
        "PAXOS\nPLAN COMMITTED", 
        "EXECUTING\nPLAN",
        "ARRIVE AT\nGOLD",
        "WAITING FOR\nPARTNER",
        "READY TO\nPICKUP",
        "CARRYING\nGOLD",
        "AT DEPOSIT",
        "GOLD DEPOSITED"
    ]
    
    # Create flow boxes
    for i, step in enumerate(steps):
        color = 'lightblue'
        if 'PAXOS' in step:
            color = 'lightgreen'
        elif 'CARRYING' in step or 'DEPOSIT' in step:
            color = 'lightyellow'
        
        box = plt.Rectangle((i*2, 0), 1.5, 1, facecolor=color, edgecolor='black', alpha=0.8)
        ax.add_patch(box)
        plt.text(i*2 + 0.75, 0.5, step, ha='center', va='center', fontweight='bold', fontsize=9)
    
    # Add arrows
    for i in range(len(steps)-1):
        plt.arrow(i*2 + 1.5, 0.5, 0.4, 0, head_width=0.1, head_length=0.1, fc='black', ec='black')
    
    # Add knowledge dependency indicators
    knowledge_points = [1, 4]  # Plan committed and partner arrival need knowledge
    for point in knowledge_points:
        plt.plot([point*2 + 0.75, point*2 + 0.75], [1, 2], 'g--', alpha=0.7)
        plt.text(point*2 + 0.75, 2.1, 'Requires\nTeam Knowledge', 
                ha='center', va='bottom', fontsize=8, bbox=dict(boxstyle="round,pad=0.2", facecolor='lightgreen'))
    
    # Add recovery paths
    recovery_points = [
        (2, "Gold\nDisappears", (3.5, -0.8), (3.5, 0)),
        (4, "Timeout", (5.5, -0.8), (5.5, 0)),
        (6, "Partners\nSeparate", (7.5, -0.8), (7.5, 0))
    ]
    
    for point, label, text_pos, arrow_start in recovery_points:
        plt.text(text_pos[0], text_pos[1], label, ha='center', va='center', 
                fontsize=8, bbox=dict(boxstyle="round,pad=0.2", facecolor='lightcoral'))
        plt.annotate('', xy=arrow_start, xytext=(text_pos[0], text_pos[1] + 0.3),
                    arrowprops=dict(arrowstyle='->', color='red', lw=2, linestyle='dashed'))
        # Return arrow to idle
        plt.annotate('', xy=(0.75, 0), xytext=(text_pos[0], text_pos[1] + 0.3),
                    arrowprops=dict(arrowstyle='->', color='red', lw=1, linestyle='dotted'))
    
    plt.xlim(-1, len(steps)*2)
    plt.ylim(-2, 3)
    plt.title("Simplified Coordination Flow with Broadcast System", size=14, pad=20)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

# Run visualizations
print("🔷 PETRI NET VISUALIZATION - LATEST VERSION WITH BROADCAST SYSTEM")
print("=" * 70)
visualize_petri_net()

print("\n🔄 SIMPLIFIED COORDINATION FLOW DIAGRAM")
print("=" * 50)
create_simplified_flow_diagram()