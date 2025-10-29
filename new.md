Challenges
• Messages take arbitrarily (random) long time
• All actions happen concurrently
• Consequence: robots are not synchronized

Things to consider
• Robots can see one another (if in field of view)
• Movement can be used to convey information
• Unlike messages, this is instantaneous

A robot can see all other robots adjacent to the same gold as it

Let’s consider the simplest case
• Only one robot finds gold
• Must find a (single!) helper
• Both have to agree on path/direction
• Have to pick up and start moving at the same time
I’ll show the CSP formulation from the finder robot side

• By default, robot is exploring
• R = (found → W)
• Once it’s found gold (adjacent position!), must wait for a partner

• By default, robot is exploring
• R = (found → (c!(msg) → W))
• Tell possible partners where it is
• Each other robot will receive this message at different time!

• By default, robot is exploring
• R = (found → (c!(id, index, xr, yr, xg, yg) → W))
• Tell possible partners where it is
• Each other robot will receive this message at different time!
• ”index” is a message number, robot specific
• E.g., if this is robot ”id=5”, found gold for first time, index is 1
• Next time ”id=5” finds gold, index will be 2
• Robot ”id=9” finds gold for first time, will send index 1
• Challenge 1: find a single partner

• By default, robot is exploring
• R = (found → (c!(id, index, xr, yr, xg, yg) → W))
• W = (c?(rsp, idp, id, index) → (c!(ack, id, idp, index) → P))
• When it receives a confirmation that matches its message index
• With the idp of partner robot, confirms the partner
• Ignores all other messages with same id
• Challenge 1: find a single partner, solved
• Every other robot that tried to partner will not receive an ack,
eventually give up
• (you could also make robots only reply if they’re within certain range)

• What if it never receives any reply (all other robots too far?)
• R = (found → SEND)
• SEND = (c!(id, index, xr, yr, xg, yg) → W)
• W = (c?(rsp, idp, id, index) → ACK) ⊓ (tout → SEND)
• ACK = (c!(ack, id, idp, index) → P)
• Introduce a timeout and re-send

Let’s consider the simplest case
• Only one robot finds gold
• Must find a (single!) helper
• done!
• Both have to agree on path/direction
• done! (assume both have identical path planning algorithms, same
result from gold to dropoff position
• Have to pick up and start moving at the same time

Let’s consider the simplest case
• Have to pick up and start moving at the same time
• Have helper go to opposite position

Have helper go to opposite position

At time t, helper arrives at opposite position
• Helper knows this
• Finder knows this
• But, could be other random robot, just exploring!
• Exploring logic must check that, if has received a message about this,
avoid this place
• Helper must send message ”Im here, it’s me”
• Finder must acknowledge

• R = (found → SEND)
• SEND = (c!(id, index, xr, yr, xg, yg) → W)
• W = (c?(rsp, idp, id, index) → ACK) ⊓ (tout → SEND)
• ACK = (c!(ack, id, idp, index) → P)
• P = (c?(here, idp, id, index) → ACK2)
• ACK2 = (move → (c!(ack2, id, idp, index) → Tw))
• Finder moves to gold, sends ack
• Now in state Tw, waiting for partner to step in as well
16 / 24
Cyber Physical Robotics
• R = (found → SEND)
• SEND = (c!(id, index, xr, yr, xg, yg) → W)
• W = (c?(rsp, idp, id, index) → ACK) ⊓ (tout → SEND)
• ACK = (c!(ack, id, idp, index) → P)
• P = (c?(here, idp, id, index) → ACK2)
• ACK2 = (move → (c!(ack2, id, idp, index) → Tw))
• Tw = (movep → (pick → T RANSP ORT))
• Finder waits to see partner move in
• Immediately after, both pick up and start moving
• One robot finds gold, done!
17 / 24
Cyber Physical Robotics
Robot in exploration mode:
• Receives a message from finder
• Avoids gold location, not to be confused by a helper
• Sends response to offer help
• Waits to receive an acknowledgement
• If it receives an ack, becomes helper
• It it reads an ack for that response to someone else, starts exploring
again
18 / 24
Cyber Physical Robotics
Second problem
• Multiple robots finding same gold at the same time
• Important: robots can see if someone else finds same gold at same
time
• If I find gold (adjacent position) and see another robot
• Either it just arrived at same time as me
• Or it’s been here a while, I just haven’t received its message yet
19 / 24
Cyber Physical Robotics
Second problem
• If a robot arrives at an adjacent position and sees other robots also
adjacent
• Move to gold position
20 / 24
Cyber Physical Robotics
Second problem
• If one robot does not move
• It was here first, it’s the original finder
• We all leave, and wait for messages (we’ll potentially be the helpers)
21 / 24
Cyber Physical Robotics
Second problem
• If all robots move to gold position
• We all arrived at precisely the same time
• Need to decide, just among ourselves, who will be the finder
• (once a finder is decided, the rest proceeds as before)
22 / 24
Cyber Physical Robotics
Second problem
• Each robot knows how many there are (N)
• This makes all the difference
• They now know how many messages they must wait for to hear from
everyone
• Each robot sends its own id to everyone else
• Once a robot has received N − 1 messages
• Can decide which one has id closest to N: that’s the finder (it 2 at
same distance, assume lower)
• Finder waits for everyone to leave
• Starts finder process
23 / 24
Communicating Sequential Processes
Quick recap:
• Process given events P = (a → (b → P))
• Sequential composition (a → (P;Q))
• Deterministic choice (external) (a → P ◻ b → Q)
• Non-deterministic choice (internal) (a → (P ⊓ Q))
• Interleaved, independent processes (P1∣∣P2)
• Interface parallel (P∣{a, b}∣Q)
24 / 24