import networkx as nx
import matplotlib.pyplot as plt

# ==============================================================
# DEFINE SIMPLIFIED PLACES & TRANSITIONS
# ==============================================================

places = [
    "P_Idle",
    "P_ExecutingPlan",
    "P_WaitingAtGold",
    "P_ReadyToPickup",
    "P_CarryingGold",
    "P_AtDeposit",
    "P_TeammateStateCache",
    "P_WaitTimer"
]

transitions = [
    "T_PlanCommitted",
    "T_ArriveAtGold",
    "T_PartnerArrives",
    "T_PickupGold",
    "T_ReachDeposit",
    "T_DepositGold",
    "T_Timeout",
    "T_GoldDisappears"
]

# ==============================================================
# DEFINE EDGES (Input → Transition → Output)
# ==============================================================

edges = [
    # Core flow
    ("P_Idle", "T_PlanCommitted"),
    ("P_TeammateStateCache", "T_PlanCommitted"),
    ("T_PlanCommitted", "P_ExecutingPlan"),

    ("P_ExecutingPlan", "T_ArriveAtGold"),
    ("T_ArriveAtGold", "P_WaitingAtGold"),
    ("T_ArriveAtGold", "P_WaitTimer"),

    ("P_WaitingAtGold", "T_PartnerArrives"),
    ("T_PartnerArrives", "P_ReadyToPickup"),

    ("P_ReadyToPickup", "T_PickupGold"),
    ("T_PickupGold", "P_CarryingGold"),

    ("P_CarryingGold", "T_ReachDeposit"),
    ("T_ReachDeposit", "P_AtDeposit"),

    ("P_AtDeposit", "T_DepositGold"),
    ("T_DepositGold", "P_Idle"),

    # Simplified recovery
    ("P_WaitingAtGold", "T_Timeout"),
    ("P_WaitTimer", "T_Timeout"),
    ("T_Timeout", "P_Idle"),

    ("P_ExecutingPlan", "T_GoldDisappears"),
    ("T_GoldDisappears", "P_Idle"),
]

# ==============================================================
# BUILD GRAPH
# ==============================================================

G = nx.DiGraph()

# Add nodes
for p in places:
    G.add_node(p, type="place")
for t in transitions:
    G.add_node(t, type="transition")

G.add_edges_from(edges)

# ==============================================================
# POSITION NODES (Clean, Layered Layout)
# ==============================================================

pos = {
    # Core
    "P_Idle": (0, 0),
    "T_PlanCommitted": (1, 0),
    "P_ExecutingPlan": (2, 0),
    "T_ArriveAtGold": (3, 0),
    "P_WaitingAtGold": (4, 0),
    "T_PartnerArrives": (5, 0),
    "P_ReadyToPickup": (6, 0),
    "T_PickupGold": (7, 0),
    "P_CarryingGold": (8, 0),
    "T_ReachDeposit": (9, 0),
    "P_AtDeposit": (10, 0),
    "T_DepositGold": (11, 0),

    # Side nodes
    "P_TeammateStateCache": (0.5, 1.5),
    "P_WaitTimer": (3.5, -1.5),
    "T_Timeout": (4.5, -1.5),
    "T_GoldDisappears": (2.5, -1.5),
}

# ==============================================================
# DRAW GRAPH
# ==============================================================

plt.figure(figsize=(14, 5))

places_nodes = [n for n, d in G.nodes(data=True) if d["type"] == "place"]
transition_nodes = [n for n, d in G.nodes(data=True) if d["type"] == "transition"]

nx.draw_networkx_nodes(G, pos, nodelist=places_nodes, node_color="#A7C7E7", node_shape="o", node_size=1800, label="Places")
nx.draw_networkx_nodes(G, pos, nodelist=transition_nodes, node_color="#FFB6B9", node_shape="s", node_size=1300, label="Transitions")

nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle="->", arrowsize=12, width=2)
nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")

plt.title("Simplified Petri Net: Robot Task Coordination", fontsize=14, fontweight="bold")
plt.axis("off")
plt.tight_layout()
plt.show()
