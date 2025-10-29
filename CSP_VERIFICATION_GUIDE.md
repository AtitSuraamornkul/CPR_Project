# Using CSP for Formal Verification Before Implementation

## Overview

Based on the CoopSys_CSP example, here's how to use **CSP (Communicating Sequential Processes)** to formally verify your robot coordination system **before writing Python code**.

---

## 🎯 Why Use CSP First?

1. **Catch design flaws early** - before implementation
2. **Verify safety properties** - deadlock, livelock, race conditions
3. **Prove correctness** - mathematical guarantee your protocol works
4. **Test edge cases** - exhaustive state space exploration
5. **Document formally** - precise specification of behavior

---

## 📚 CSP Methodology (Based on CoopSys Example)

### **Step 1: Define Your System Components as FSMs**

Each robot and component is modeled as a Finite State Machine (FSM).

**Example from CoopSys_CSP/RoboMng_fsm.csp:**
```csp
RoboMng(ID) = let
  -- State: Approach
  Approach(rdy) = 
    obs.APPROACH.ID
    -> out.dest!Box
    -> Select(rdy)
  
  -- State: Ready
  Ready(rdy,prm) = 
    obs.READY.ID
    -> out.ready
    -> (if (rdy) then Transport(prm) else Select)
  
  -- State: Transport
  Transport(prm) = 
    obs.TRANSPORT.ID
    -> out.dest!Goal
    -> Select
    
  -- State: Return
  Return(chg,bsy) = 
    obs.RETURN.ID
    -> out.dest!Home
    -> Return_Charge(chg,bsy,False)
    
within Start
```

**For Your Robot System:**
- Model each robot's state machine (idle, moving_to_gold, waiting_at_gold, etc.)
- Define Paxos proposer/acceptor FSMs
- Model message passing with delays

---

### **Step 2: Define Messages and Events**

**Example from CoopSys.csp:**
```csp
datatype RTC_ev
 = comp | new | start | ready | dest.Arvs | arrive.Arvs
 | full | low | cancel
 | velocity.Vels | pose.Poss | position.Poss | sensor.Sens

datatype RTC_msg
  = APPROACH.IDs | READY.IDs | TRANSPORT.IDs | RETURN.IDs | CHARGE.IDs
```

**For Your System:**
```csp
-- Robot states
datatype RobotState = Idle | MovingToGold | WaitingAtGold | ReadyToPickup 
                    | CarryingGold | AtDeposit

-- Paxos messages
datatype PaxosMsg = Prepare.ProposalID | Promise.ProposalID.Value
                  | Accept.ProposalID.Value | Accepted.ProposalID
                  | Commit.Plan

-- Robot events
datatype RobotEvent = observe.GoldPos | move.Direction | pickup | deposit
                    | timeout | partner_arrived

-- Message delays
DelayRange = {1..5}  -- 1-5 step delays
```

---

### **Step 3: Define Communication Links**

**Example from CoopSys.csp:**
```csp
Link(1,2) = {| ready,cancel,comp |}
Link(1,3) = {| dest,start |}
Link(3,1) = {| arrive,low,full |}
Link(7,1) = {| new,start |}
Link(1,7) = {| comp |}
```

**For Your System:**
```csp
-- Robot 1 can send to Robot 2 (same group)
Link(1,2) = {| paxos_prepare, paxos_promise, paxos_accept, 
               state_update, at_gold, ready_pickup |}

-- Robot 2 can send to Robot 1
Link(2,1) = {| paxos_prepare, paxos_promise, paxos_accept,
               state_update, at_gold, ready_pickup |}

-- No communication between groups
Link(1,11) = {}  -- Robot 1 (group 1) cannot talk to Robot 11 (group 2)
```

---

### **Step 4: Model Message Delays**

**Add delay buffer to composition:**
```csp
-- Delayed message buffer
DelayBuffer(capacity) = let
  Var(queue)
    = (#queue > 0) & tock -> out!head(queue) -> Var(tail(queue))
    [] (#queue < capacity) & in?msg -> 
       let delay = random(1,5)  -- Random delay 1-5 steps
       within Var(queue ^ <(msg, delay)>)
    [] tock -> Var(decrement_delays(queue))
within Var(<>)
```

---

### **Step 5: Compose the System**

**Example from CoopSys.csp:**
```csp
FSM(1) = RoboMng(1)
FSM(2) = RoboMng(2)
FSM(3) = RoboCtrl
FSM(4) = RoboCtrl
FSM(5) = RaspberryPiMouse(1)
FSM(6) = RaspberryPiMouse(2)
FSM(7) = Client

CoopSys = RTM_compo(FSM, Link, 4, False)
```

**For Your System:**
```csp
-- 10 robots per group
FSM(1) = Robot(1, Group1)
FSM(2) = Robot(2, Group1)
...
FSM(10) = Robot(10, Group1)
FSM(11) = Robot(11, Group2)
...
FSM(20) = Robot(20, Group2)

-- Grid environment
FSM(21) = Grid

-- Compose with message delays
RobotSystem = RTM_compo_delayed(FSM, Link, BufferSize=5, Delays=True)
```

---

### **Step 6: Define Safety Specifications**

**Example from CoopSys_spec.csp:**
```csp
-- Check that TRANSPORT operations don't conflict
SafeSpec = Spec_simul(
  {TRANSPORT.1},      -- When Robot 1 transports
  {TRANSPORT.2, RETURN.1},  -- Robot 2 must transport or R1 returns
  {TRANSPORT.2},      -- When Robot 2 transports
  {TRANSPORT.1, RETURN.2}   -- Robot 1 must transport or R2 returns
)
```

**For Your System:**
```csp
-- Safety: No two pairs pick up same gold
NoDoublePickup = 
  pickup.R1.R2.Pos -> (not pickup.R3.R4.Pos) -> NoDoublePickup

-- Safety: Partners must be at same position to pickup
PartnerSync = 
  pickup.R1.R2.Pos -> (position.R1.Pos and position.R2.Pos) -> PartnerSync

-- Safety: Gold not dropped during coordinated movement
NoGoldDrop = 
  carrying.R1.R2 -> (move.R1.Dir and move.R2.Dir => Dir==Dir) -> NoGoldDrop

-- Liveness: Eventually gold gets deposited
EventuallyDeposit = 
  observe.Gold -> eventually(deposit.Gold)

-- Paxos Safety: At most one value decided per round
PaxosSafety = 
  commit.Plan1 -> (not commit.Plan2) where Plan1 != Plan2
```

---

### **Step 7: Write Verification Assertions**

**Example from CoopSys.csp:**
```csp
-- Trace refinement: System refines specification
assert SafeSpec [T= CoopSys

-- Deadlock freedom
assert CoopSys \ {|obs|} :[deadlock free [F]]

-- Livelock freedom
assert CoopSys \ {|obs|} :[livelock free [FD]]

-- Test case conformance
assert CoopSys \ {tock} [T= TestCase
```

**For Your System:**
```csp
-- Safety properties
assert NoDoublePickup [T= RobotSystem
assert PartnerSync [T= RobotSystem
assert NoGoldDrop [T= RobotSystem
assert PaxosSafety [T= RobotSystem

-- Deadlock/Livelock
assert RobotSystem \ {|obs|} :[deadlock free [F]]
assert RobotSystem \ {|obs|} :[livelock free [FD]]

-- With message delays
assert RobotSystem_Delayed :[deadlock free [F]]
assert RobotSystem_Delayed :[livelock free [FD]]

-- Verify delayed system still satisfies safety
assert NoDoublePickup [T= RobotSystem_Delayed
```

---

## 🔧 How to Use FDR4 (Model Checker)

### **Installation:**
1. Download FDR4 from https://cocotec.io/fdr/
2. Free for academic use
3. Available for Windows, Mac, Linux

### **Verification Process:**
```bash
1. Write your CSP model in .csp files
2. Open main file (e.g., RobotSystem.csp) in FDR4
3. Click "Run All" to check all assertions
4. FDR4 will:
   - Explore entire state space
   - Check all assertions
   - Report: ✓ Pass or ✗ Fail with counterexample
```

### **Interpreting Results:**
- **✓ Green checkmark** = Property verified for ALL possible executions
- **✗ Red X** = Counterexample found (shows trace that violates property)
- **Counterexample** = Exact sequence of events that breaks your design

---

## 📝 Workflow: CSP → Python Implementation

```
┌─────────────────────────────────────────────────────────┐
│  1. Model System in CSP                                 │
│     - Define FSMs for each robot                        │
│     - Define message types and delays                   │
│     - Specify communication topology                    │
├─────────────────────────────────────────────────────────┤
│  2. Write Safety/Liveness Specifications                │
│     - No double pickup                                  │
│     - Partner synchronization                           │
│     - Paxos correctness                                 │
│     - Deadlock/livelock freedom                         │
├─────────────────────────────────────────────────────────┤
│  3. Verify with FDR4                                    │
│     - Run model checker                                 │
│     - Get counterexamples if properties fail            │
├─────────────────────────────────────────────────────────┤
│  4. Fix Design Issues in CSP                            │
│     - Adjust FSM transitions                            │
│     - Add timeouts, retries                             │
│     - Refine Paxos protocol                             │
│     - Re-verify until all properties pass               │
├─────────────────────────────────────────────────────────┤
│  5. Implement in Python                                 │
│     - Translate verified FSMs to Python classes         │
│     - Implement message passing as modeled              │
│     - Add delays as specified                           │
│     - Confidence: Design is proven correct!             │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Specific Issues to Model for Your System

### **1. Message Delay Impact on Paxos**
```csp
-- Model: Can Paxos reach consensus with 1-5 step delays?
PaxosWithDelays = 
  Proposer [|msgs|] DelayBuffer(5) [|msgs|] Acceptor

assert PaxosConsensus [T= PaxosWithDelays
```

### **2. Partner Coordination with Delays**
```csp
-- Model: Do partners arrive at gold within timeout window?
PartnerCoordination = 
  Robot1 [|{at_gold, ready_pickup}|] DelayBuffer(5) [|msgs|] Robot2

assert NoTimeout [T= PartnerCoordination
```

### **3. Duplicate Gold Assignment**
```csp
-- Model: Can two proposals assign same gold?
GoldAssignment = 
  Proposer1 [|{gold_pos}|] Proposer2

assert UniqueAssignment [T= GoldAssignment
```

---

## 📖 Example: Modeling Your Robot FSM

```csp
Robot(ID, Group) = let

  -- State: Idle
  Idle = 
    observe?gold_pos -> 
      (random_propose() & propose.gold_pos -> Preparing
       [] explore -> Idle)
  [] state_update?teammate_state -> Idle
  [] tock -> Idle

  -- State: Preparing (Paxos Phase 1)
  Preparing(proposal_id) = 
    send.prepare.proposal_id -> WaitingPromises(proposal_id, {})
  
  WaitingPromises(pid, promises) = 
    receive.promise.pid?from -> 
      let new_promises = union(promises, {from})
      within (if (#new_promises > GroupSize/2) 
              then Proposing(pid) 
              else WaitingPromises(pid, new_promises))
  [] timeout -> Backoff
  [] tock -> WaitingPromises(pid, promises)

  -- State: Proposing (Paxos Phase 2)
  Proposing(pid) = 
    send.accept.pid.plan -> WaitingAccepts(pid, {})
  
  WaitingAccepts(pid, accepts) = 
    receive.accepted.pid?from -> 
      let new_accepts = union(accepts, {from})
      within (if (#new_accepts > GroupSize/2) 
              then send.commit.plan -> MovingToGold(plan)
              else WaitingAccepts(pid, new_accepts))
  [] timeout -> Backoff
  [] tock -> WaitingAccepts(pid, accepts)

  -- State: MovingToGold
  MovingToGold(target) = 
    move.towards(target) -> 
      (if (at_position(target)) 
       then WaitingAtGold(target)
       else MovingToGold(target))
  [] tock -> MovingToGold(target)

  -- State: WaitingAtGold
  WaitingAtGold(pos) = 
    send.at_gold.partner -> CheckPartner(pos, 0)
  
  CheckPartner(pos, timer) = 
    receive.ready_pickup.partner -> ReadyToPickup(pos)
  [] tock -> (if (timer > 20) 
              then Timeout -> Idle
              else CheckPartner(pos, timer+1))

  -- State: ReadyToPickup
  ReadyToPickup(pos) = 
    pickup.pos -> CarryingGold(deposit_pos)

  -- State: CarryingGold
  CarryingGold(deposit) = 
    move.towards(deposit) -> 
      (if (at_position(deposit)) 
       then deposit -> Idle
       else CarryingGold(deposit))
  [] partner_moved_different_direction -> 
      drop_gold -> Idle
  [] tock -> CarryingGold(deposit)

within Idle
```

---

## ✅ Benefits of This Approach

1. **Find bugs before coding** - CSP finds race conditions, deadlocks
2. **Mathematical proof** - FDR4 proves correctness for ALL executions
3. **Clear specification** - CSP model documents exact behavior
4. **Confidence** - Implementation follows verified design
5. **Report material** - Show formal verification in your report

---

## 🚀 Next Steps for Your Project

1. **Start simple**: Model 2 robots coordinating on 1 gold piece
2. **Add complexity**: Scale to 4 robots, 2 gold pieces
3. **Add delays**: Model message delays and verify Paxos still works
4. **Verify properties**: Check all safety/liveness properties
5. **Fix issues**: Refine design based on counterexamples
6. **Implement**: Translate verified CSP to Python with confidence

---

## 📚 Resources

- **FDR4 Manual**: https://cocotec.io/fdr/manual/
- **CSP Tutorial**: "Understanding Concurrent Systems" by A.W. Roscoe
- **CoopSys Paper**: IEICE Transactions on Information and Systems, Vol.E104-D, No.10, October 2021
- **Your Example**: `/CoopSys_CSP/` folder has complete working example

---

## 💡 Key Insight

**CSP verification = Design-time bug detection**

Instead of:
```
Design → Implement → Test → Find bug → Redesign → Repeat
```

Do:
```
Design in CSP → Verify → Fix design → Verify → Implement once correctly
```

This is **exactly what the course wants**: formal methods for distributed systems!
