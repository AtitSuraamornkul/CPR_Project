from graphviz import Digraph

# Create a directed graph
dot = Digraph("Robot_Petri_Net", format="png")
dot.attr(rankdir="LR", size="8,5")

# Define places (circles)
places = [
    "wandering", "moving_to_gold", "at_gold",
    "waiting_for_partner", "forming_pair",
    "carrying_gold", "at_deposit"
]
for p in places:
    dot.node(p, p, shape="circle")

# Define transitions (rectangles)
transitions = [
    "find_gold", "reach_gold", "propose_pickup",
    "partner_accepts", "form_pair", "reach_deposit",
    "deposit_gold", "lose_partner", "timeout"
]
for t in transitions:
    dot.node(t, t, shape="box", style="filled", color="lightgray")

# Define arcs (edges)
edges = [
    ("wandering", "find_gold"), ("find_gold", "moving_to_gold"),
    ("moving_to_gold", "reach_gold"), ("reach_gold", "at_gold"),
    ("at_gold", "propose_pickup"), ("propose_pickup", "waiting_for_partner"),
    ("waiting_for_partner", "partner_accepts"), ("partner_accepts", "forming_pair"),
    ("forming_pair", "form_pair"), ("form_pair", "carrying_gold"),
    ("carrying_gold", "reach_deposit"), ("reach_deposit", "at_deposit"),
    ("at_deposit", "deposit_gold"), ("deposit_gold", "wandering"),

    # Exceptional cases
    ("waiting_for_partner", "timeout"), ("timeout", "wandering"),
    ("forming_pair", "lose_partner"), ("lose_partner", "at_gold"),
]

for src, dst in edges:
    dot.edge(src, dst)

# Save and render
dot.render("robot_petri_net", view=True)
print("✅ Petri net visualization saved to robot_petri_net.png")
