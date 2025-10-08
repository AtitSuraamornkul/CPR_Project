# CPR_Project
Cyber Physical Robots: Term project
August 9, 2025
1 Overview
The goal of this project is to demonstrate mastery of the concepts of Cyber Physical Robotics, including distributed design, mathematical formalisms for distributed systems, and simulation methodologies. This mastery will be demonstrated through the design and implementation of several simulations and an
associated report, describing this process.
The final simulation must encompass:
• A grid-world of (i.e., square matrix) of 20x20.
• 2 groups of robots: each group consists of 10 robots. Robots in each group
may communicate with each other, but not with the other group. Each
robot can ”see” 8 positions, depending on the direction it’s facing: the 3
position directly in front, in the next row/column, and the 5 after that
(e.g., assuming x and y grow in the east and north directions, respectively: if a robot is at position (5,5), facing north, it can observe positions
(4,6),(5,6),(6,6) and (3,7),(4,7),(5,7),(6,7),(7.7)).
• Each robot must have its dedicated control logic, responding only to its
history, currently sensed positions, and whatever messages it has received
thus far.
• At each simulation step, each robot may either change facing direction,
move one position in the direction it’s facing, or perform an action on the
current position. Several robots may occupy the same position at once.
• Apart from robots, in each position there is either: nothing; one or more
gold bars; a deposit point. In the whole grid, there should be only 2
deposit points, one per robot group (robots are allowed to know where
these are). Gold bars should be initialized at random.
• A gold bar can be picked up from a position if and only if two robots
of the same group are on that position, and exactly two of them perform
the action pick up on a simulation step. If only one, or more than 2, try
to do this, picking up fails. If 4 robots (2 from each group) all attempt
1
to pick up simultaneously, each gets a gold bar if there are at least 2 gold
bars on that position: if only 1, both groups fail.
• Once a pair of robots is holding a gold bar, they can move it if they both
move in the same direction at each simulation time step. If they fail to do
so (i.e., move in different directions) the gold bar is dropped.
• If robots can reach the deposit point while carrying a gold bar, the bar
disappears, and that group gets a point.
At each submission milestone, students will provide an updated simulation
where robot control and coordination is improved, using the concepts learned in
the course so far. The report at each milestone must describe the mathematics,
and corresponding description of software implementation, of those concepts in
the simulation.
2 Assessment
Assessment will prioritize students’ demonstration of mastery over the course’s
learning objectives, rather than the sophistication of the prototype. However,
it is a necessary pre-condition that the prototype works.
Each assessment milestone accounts for 25% of the final grade.
3 Timeline
There are 4 milestones throughout the term. At each milestone, you must upload
the report thus far, and demonstrate current working simulation, up until the
current level of development.
1. 12 of September
2. 03 of October
3. 24 of October
4. 21 of November