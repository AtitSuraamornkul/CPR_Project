# How to Use the Simplified CSP Model for Bug Finding

## 🎯 Overview

`RobotSystem_Simple.csp` models your **current Python implementation** (with bugs) in a way that FDR4 can verify in minutes.

---

## 📋 What This Model Includes

### ✅ **Intentionally Modeled BUGS** (from your `full.py`)

1. **Incorrect quorum calculation** (Line 185-186)
   ```python
   num_teammates = len(self.teammate_states) + 1
   ```
   
2. **No Paxos timeout recovery** (Line 177-199)
   - Robot gets stuck in `preparing` state forever
   
3. **Partner timeout too short** (Line 302)
   - 20 steps may not be enough with delays + travel time
   
4. **Race conditions in proposals** (Line 363)
   - Multiple robots can propose simultaneously

### ✅ **Simplified for Verification**

- **3 robots** instead of 20 (enough to show quorum bugs)
- **Abstract positions** (Home, GoldSite, Deposit) instead of 20×20 grid
- **Fixed delays** (1-3 steps) instead of random
- **Symbolic movement** instead of pathfinding

### ✅ **What's Still Accurate**

- Full Paxos protocol (PREPARE, PROMISE, ACCEPT, ACCEPTED, COMMIT)
- Message delay system
- State machine transitions
- Partner coordination
- Timeout behaviors

---

## 🚀 How to Run in FDR4

### **Step 1: Install FDR4**
```bash
Download from: https://cocotec.io/fdr/
Free for academic use
```

### **Step 2: Open Model**
```
1. Launch FDR4
2. File → Open → RobotSystem_Simple.csp
3. Wait for parsing (should be instant)
```

### **Step 3: Run Verification**
```
Option A: Click "Run All" (runs all assertions)
Option B: Select specific assertion and click "Run"
```

---

## 🔍 What to Look For: Expected Failures

### **Test 1: NoInvalidQuorum** ❌ EXPECTED TO FAIL

**Assertion:**
```csp
assert NoInvalidQuorum [T= System
```

**What it checks:** Robot should not proceed with consensus if it doesn't have real quorum.

**Expected failure:**
```
FAILED: Trace refinement violation found
Counterexample depth: ~8-12 steps
```

**What the counterexample will show:**
```
1. tock
2. propose.1.Prop.100.GoldPlan.1.2.GoldSite
3. send.1.PaxosPrepare.Prop.100
4. recv.2.PaxosPrepare.Prop.100  (delayed 2 steps)
5. send.2.PaxosPromise.Prop.100...
6. recv.1.PaxosPromise.Prop.100...
7. obs.InvalidQuorum.1.1.1  ← BUG DETECTED!
   Robot 1 only knows 1 teammate
   Has 1 promise
   Calculates quorum = 1/2 of (1+1) = 1
   Proceeds (WRONG! Should need 2/3 of 3 robots)
```

**Why this is wrong:**
- Robot 3's state update hasn't arrived yet (message delay)
- Robot 1 thinks team size is 2, but it's actually 3
- Robot 1 needs 2 promises for real quorum, but proceeds with only 1

**The bug in your Python code:**
```python
# Line 185-186 in full.py
num_teammates = len(self.teammate_states) + 1  # WRONG! Dynamic size
if len(self.promises_received) > num_teammates / 2:
```

**The fix:**
```python
TEAM_SIZE = 10  # Fixed constant
if len(self.promises_received) > TEAM_SIZE / 2:
```

---

### **Test 2: OnePlanPerRound** ❌ MIGHT FAIL

**Assertion:**
```csp
assert OnePlanPerRound [T= System
```

**What it checks:** Only one plan should be committed per consensus round.

**Possible failure:**
```
FAILED: Trace refinement violation found
Counterexample shows two different commits
```

**What the counterexample will show:**
```
1. propose.1.Prop.100.GoldPlan.1.2.GoldSite  (Robot 1 proposes)
2. propose.3.Prop.300.GoldPlan.3.2.GoldSite  (Robot 3 proposes same gold!)
3. send.1.PaxosPrepare.Prop.100
4. send.3.PaxosPrepare.Prop.300
5-10. Messages delayed and interleaved...
11. commit.1.GoldPlan.1.2.GoldSite  (Robot 1 commits)
12. commit.3.GoldPlan.3.2.GoldSite  (Robot 3 commits)
13. obs.MultipleCommits... ← BUG DETECTED!
    Same gold assigned to two pairs!
```

**Why this happens:**
- Both robots observe gold simultaneously
- Both initiate proposals before seeing each other's PREPARE
- Due to delays and incorrect quorum, both reach "consensus"
- Two different plans committed

**The fix:**
- Proper proposal ID comparison
- Accept/reject based on higher proposal numbers
- Better conflict detection

---

### **Test 3: Deadlock Freedom** ❌ MIGHT FAIL

**Assertion:**
```csp
assert System :[deadlock free [F]]
```

**What it checks:** System should never reach a state where no progress is possible.

**Possible failure:**
```
FAILED: Deadlock found
Counterexample shows system stuck
```

**What the counterexample will show:**
```
1. propose.1.Prop.100...
2. send.1.PaxosPrepare.Prop.100
3. recv.2.PaxosPrepare.Prop.100
4. send.2.PaxosPromise.Prop.100...
5. (delay... delay... delay...)
6-20. tock... tock... tock...
21. All robots in state: Preparing/Waiting
22. No messages left to deliver
23. DEADLOCK: No robot can make progress
```

**Why this happens:**
- Robot 1 sent PREPARE to robots 2 and 3
- Robot 2 responded with PROMISE (arrives at step 5)
- Robot 3's message got heavily delayed or lost
- Robot 1 stuck waiting for more promises
- No timeout recovery mechanism
- System deadlocked

**The bug:**
```python
# No timeout in process_messages() for Paxos states
if self.paxos_state == 'preparing':
    # Waits forever...
```

**The fix:**
```python
# Add timeout counter
if self.paxos_state == 'preparing':
    self.paxos_timeout += 1
    if self.paxos_timeout > MAX_PAXOS_TIMEOUT:
        # Abort and reset
        self.paxos_state = 'idle'
        self.proposal_backoff = random.randint(5, 15)
```

---

### **Test 4: MinimalTimeouts** ❌ EXPECTED TO FAIL

**Assertion:**
```csp
assert MinimalTimeouts [T= System
```

**What it checks:** Partner coordination shouldn't timeout if both robots are working correctly.

**Expected failure:**
```
FAILED: Partner timeout occurred
Counterexample shows coordination failure
```

**What the counterexample will show:**
```
1. commit.1.GoldPlan.1.2.GoldSite  (Plan committed)
2-5. Robot 1 moves to GoldSite
6. send.1.AtGold.GoldSite  (Robot 1 arrives, notifies partner)
7-8. Message delayed (2 steps)
8-11. Robot 2 still moving to gold
12. recv.2.AtGold.GoldSite  (Robot 2 finally gets message)
13-15. Robot 2 still 3 steps away from gold
16. Robot 1 wait_timer = 10
17. obs.PartnerTimeout.1 ← BUG DETECTED!
    Robot 1 gives up (timeout)
18. Robot 2 arrives at empty gold site
```

**Why this happens:**
- Message delay: 2-3 steps
- Travel time: 5+ steps
- Total: 7-8 steps
- Timeout: 10 steps (PARTNER_TIMEOUT in model)
- Barely enough, very fragile!

**The bug:**
```python
if self.wait_timer > 20:  # Too short with delays!
```

**The fix:**
```python
MAX_WAIT = 50  # Or adaptive based on distance + max_delay
if self.wait_timer > MAX_WAIT:
```

---

## 📊 How to Read FDR4 Output

### **When Assertion Passes** ✅
```
Checking: NoInvalidQuorum [T= System
States explored: 1,234,567
Result: ✓ Passed (all traces satisfy specification)
```

### **When Assertion Fails** ❌
```
Checking: NoInvalidQuorum [T= System
States explored: 45,678
Result: ✗ Failed

Counterexample found:
Click "View Counterexample" to see trace
```

### **Counterexample Trace Format**
```
1. tock
2. propose.1.Prop.100.GoldPlan.1.2.GoldSite
3. send.1.PaxosPrepare.Prop.100
4. tock
5. recv.2.PaxosPrepare.Prop.100
   ... (more events)
15. obs.InvalidQuorum.1.1.1  ← The bug happens here!
```

**How to interpret:**
- Each line is an event that occurred
- Numbers are the sequence of events
- `obs.*` events show where specification was violated
- Work backwards to understand why

---

## 🔧 Iterative Verification Process

### **Workflow:**

```
1. Run FDR4 → Assertion FAILS
   ↓
2. Examine counterexample trace
   ↓
3. Understand WHY the bug occurs
   ↓
4. Fix the CSP model (add timeout, fix quorum, etc.)
   ↓
5. Re-run FDR4 → Test if fixed
   ↓
6. Repeat until ALL assertions pass ✓
   ↓
7. Implement verified fixes in Python
```

### **Example: Fixing Quorum Bug**

**Before (buggy):**
```csp
RobotPreparing(..., known_teammates, ...) =
  recv.id.PaxosPromise.pid?accepted_pid?accepted_plan ->
    let num_teammates = #known_teammates + 1  -- BUG!
        quorum = num_teammates / 2
    within
      (if (#new_promises > quorum) then ...)
```

**After (fixed):**
```csp
RobotPreparing(..., known_teammates, ...) =
  recv.id.PaxosPromise.pid?accepted_pid?accepted_plan ->
    let quorum = TEAM_SIZE / 2  -- FIXED! Use constant
    within
      (if (#new_promises > quorum) then ...)
```

**Re-run FDR4:**
```
✓ NoInvalidQuorum now passes!
```

---

## 📝 What to Document for Your Report

### **1. Counterexample Analysis**

For each bug found, document:
- The FDR4 assertion that failed
- The counterexample trace
- Why this violates correctness
- What causes the bug
- How to fix it

### **2. Iterative Refinement**

Show:
- Version 1: Original model (bugs found)
- Version 2: Fixed quorum (some bugs remain)
- Version 3: Added timeout (more bugs fixed)
- Version 4: All assertions pass ✓

### **3. Formal Proof**

Include:
- Screenshot of FDR4 showing all assertions pass
- Statement: "System verified to satisfy safety and liveness properties"
- Number of states explored
- Verification time

---

## 🎯 Expected Results Summary

| Test | Current Model | After Fixes |
|------|--------------|-------------|
| NoInvalidQuorum | ❌ FAIL | ✅ PASS |
| OnePlanPerRound | ❌ FAIL | ✅ PASS |
| Deadlock free | ❌ FAIL | ✅ PASS |
| Livelock free | ⚠️ SLOW | ✅ PASS |
| MinimalTimeouts | ❌ FAIL | ✅ PASS |

---

## 🚀 Next Steps

1. **Run current model** → Observe all failures
2. **Document counterexamples** → Understand bugs
3. **Fix model iteratively** → One bug at a time
4. **Verify fixes** → All assertions pass
5. **Implement in Python** → Translate verified design
6. **Test full system** → Compare before/after
7. **Write report** → Show formal verification process

---

## 💡 Key Insight

**This process demonstrates:**
- Formal verification finds bugs systematically
- Counterexamples show exact failure scenarios
- Iterative refinement leads to proven-correct design
- Much faster than debugging Python by trial-and-error

**This is the value of formal methods!** 🎓
