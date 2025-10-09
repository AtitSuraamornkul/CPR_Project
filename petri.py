import matplotlib.pyplot as plt
import networkx as nx

def visualize_petri_net():
    # Create directed graph
    G = nx.DiGraph()
    
    # Add Places (States)
    places = [
        'P_Idle', 'P_ExecutingPlan', 'P_WaitingAtGold', 
        'P_ReadyToPickup', 'P_CarryingGold', 'P_AtDeposit'
    ]
    
    # Add Transitions (Events)
    transitions = [
        'T_PlanCommitted', 'T_ArriveAtGold', 'T_PartnerArrives',
        'T_PickupGold', 'T_ReachDeposit', 'T_DepositGold',
        'T_Timeout', 'T_GoldDisappears', 'T_PartnersSeparate'
    ]
    
    # Add all nodes
    for place in places:
        G.add_node(place, node_type='place', shape='ellipse')
    for transition in transitions:
        G.add_node(transition, node_type='transition', shape='rectangle')
    
    # Define edges (Place → Transition → Place)
    edges = [
        # Normal workflow
        ('P_Idle', 'T_PlanCommitted'),
        ('T_PlanCommitted', 'P_ExecutingPlan'),
        ('P_ExecutingPlan', 'T_ArriveAtGold'),
        ('T_ArriveAtGold', 'P_WaitingAtGold'),
        ('P_WaitingAtGold', 'T_PartnerArrives'),
        ('T_PartnerArrives', 'P_ReadyToPickup'),
        ('P_ReadyToPickup', 'T_PickupGold'),
        ('T_PickupGold', 'P_CarryingGold'),
        ('P_CarryingGold', 'T_ReachDeposit'),
        ('T_ReachDeposit', 'P_AtDeposit'),
        ('P_AtDeposit', 'T_DepositGold'),
        ('T_DepositGold', 'P_Idle'),
        
        # Recovery transitions
        ('P_WaitingAtGold', 'T_Timeout'),
        ('T_Timeout', 'P_Idle'),
        ('P_ExecutingPlan', 'T_GoldDisappears'),
        ('P_WaitingAtGold', 'T_GoldDisappears'),
        ('T_GoldDisappears', 'P_Idle'),
        ('P_CarryingGold', 'T_PartnersSeparate'),
        ('T_PartnersSeparate', 'P_Idle')
    ]
    
    G.add_edges_from(edges)
    
    # Create layout
    pos = {
        # Places - left to right flow
        'P_Idle': (0, 2),
        'P_ExecutingPlan': (2, 2),
        'P_WaitingAtGold': (4, 2),
        'P_ReadyToPickup': (6, 2),
        'P_CarryingGold': (8, 2),
        'P_AtDeposit': (10, 2),
        
        # Transitions - between places
        'T_PlanCommitted': (1, 2),
        'T_ArriveAtGold': (3, 2),
        'T_PartnerArrives': (5, 2),
        'T_PickupGold': (7, 2),
        'T_ReachDeposit': (9, 2),
        'T_DepositGold': (11, 2),
        
        # Recovery transitions - below main flow
        'T_Timeout': (4, 0),
        'T_GoldDisappears': (3, 0),
        'T_PartnersSeparate': (8, 0)
    }
    
    # Draw the graph
    plt.figure(figsize=(15, 8))
    
    # Draw places as ellipses
    place_nodes = [node for node in G.nodes if G.nodes[node]['node_type'] == 'place']
    nx.draw_networkx_nodes(G, pos, nodelist=place_nodes, 
                          node_shape='o', node_size=2000, 
                          node_color='lightblue', alpha=0.7)
    
    # Draw transitions as rectangles
    transition_nodes = [node for node in G.nodes if G.nodes[node]['node_type'] == 'transition']
    nx.draw_networkx_nodes(G, pos, nodelist=transition_nodes, 
                          node_shape='s', node_size=1500, 
                          node_color='lightcoral', alpha=0.7)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, 
                          arrowsize=20, arrowstyle='->')
    
    # Draw labels
    labels = {node: node for node in G.nodes}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    plt.title("Robot Coordination Petri Net", size=16)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

# Run the visualization
visualize_petri_net()