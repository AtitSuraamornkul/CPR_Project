# How to Use CSP for Verification BEFORE Coding

## 🎯 Quick Start

You have **CoopSys_CSP** as a reference example. Here's how to apply it to your robot system:

---

## 📋 Step-by-Step Process

### **1. Install FDR4 Model Checker**
```bash
# Download from: https://cocotec.io/fdr/
# Free for academic use
# Install on your system
```

### **2. Study the CoopSys Example**
```bash
cd CoopSys_CSP/
# Open CoopSys.csp in FDR4
# Click "Run All" to see verification in action
```

**Key files to understand:**
- `CoopSys.csp` - Main composition file
- `RoboMng_fsm.csp` - FSM example (your robot states)
- `CoopSys_spec.csp` - Safety specifications
- `RTM_compo.csp` - How components are composed with buffers

---

### **3. Model Your Robot System**

I've created a **starter template** for you: `RobotSystem.csp`

**What's included:**
- ✅ Robot FSM with all your states (Idle, MovingToGold, WaitingAtGold, etc.)
- ✅ Paxos protocol (Preparing, Proposing, Accepting)
- ✅ Message delay buffers (1-5 step delays)
- ✅ Safety specifications (NoDoublePickup, PartnerSync, PaxosSafety)
- ✅ Verification assertions

**Customize it:**
```csp
-- Adjust these to match your needs:
NumRobots = 10
GoldPositions = {Pos.5.5, Pos.10.10, Pos.15.15}
MinDelay = 1
MaxDelay = 5
```

---

### **4. Verify Properties BEFORE Coding**

Open `RobotSystem.csp` in FDR4 and run:

```csp
-- These assertions will be checked:
assert NoDoublePickup [T= RobotSystem
assert PartnerSync [T= RobotSystem  
assert PaxosSafety [T= RobotSystem
assert RobotSystem :[deadlock free [F]]
assert RobotSystem :[livelock free [FD]]
```

**What FDR4 does:**
- Explores ALL possible execution paths
- Checks if properties hold in EVERY case
- If property fails → gives you exact counterexample trace

---

### **5. Interpret Results**

#### ✅ **If All Pass:**
```
✓ NoDoublePickup verified
✓ PartnerSync verified
✓ PaxosSafety verified
✓ Deadlock free
✓ Livelock free
```
→ **Your design is mathematically proven correct!**
→ **Safe to implement in Python**

#### ❌ **If Something Fails:**
```
✗ PaxosSafety FAILED
Counterexample trace:
  Step 1: Robot 1 sends Prepare(101)
  Step 2: Robot 2 sends Prepare(201)
  Step 3: Robot 3 promises to 101
  Step 4: Robot 4 promises to 201
  Step 5: Split brain - no quorum!
```
→ **Fix the CSP model**
→ **Re-verify until it passes**
→ **Then implement the corrected design**

---

## 🔍 What to Verify for Your System

### **Critical Properties:**

1. **No Double Pickup** (Safety)
   ```csp
   -- Same gold cannot be picked up by two pairs
   assert NoDoublePickup [T= RobotSystem
   ```

2. **Partner Synchronization** (Safety)
   ```csp
   -- Partners must be at same position to pickup
   assert PartnerSync [T= RobotSystem
   ```

3. **Paxos Correctness** (Safety)
   ```csp
   -- At most one plan decided per round
   assert PaxosSafety [T= RobotSystem
   ```

4. **Deadlock Freedom** (Liveness)
   ```csp
   -- System never gets stuck
   assert RobotSystem :[deadlock free [F]]
   ```

5. **Livelock Freedom** (Liveness)
   ```csp
   -- System doesn't loop forever without progress
   assert RobotSystem :[livelock free [FD]]
   ```

6. **Message Delay Tolerance** (Robustness)
   ```csp
   -- System works even with 1-5 step delays
   assert RobotSystem_Delayed :[deadlock free [F]]
   ```

---

## 🛠️ Workflow

```
┌──────────────────────────────────────────────────┐
│ 1. Model in CSP (RobotSystem.csp)               │
│    - Define robot FSMs                           │
│    - Define Paxos protocol                       │
│    - Add message delays                          │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│ 2. Verify with FDR4                              │
│    - Run model checker                           │
│    - Check all assertions                        │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
         ┌───────┴────────┐
         │                │
         ▼                ▼
    ✅ PASS          ❌ FAIL
         │                │
         │                ▼
         │    ┌──────────────────────┐
         │    │ 3. Analyze Counter-  │
         │    │    example           │
         │    └──────────┬───────────┘
         │               │
         │               ▼
         │    ┌──────────────────────┐
         │    │ 4. Fix CSP Model     │
         │    └──────────┬───────────┘
         │               │
         │               └─────────┐
         │                         │
         ▼                         ▼
┌──────────────────────────────────────────────────┐
│ 5. Implement in Python (full.py)                │
│    - Translate verified FSMs                     │
│    - Implement message delays                    │
│    - Confidence: Design is proven!               │
└──────────────────────────────────────────────────┘
```

---

## 📖 Learning from CoopSys Example

### **Key Patterns to Copy:**

1. **FSM Structure** (from `RoboMng_fsm.csp`):
   ```csp
   Robot(ID) = let
     State1 = ... -> State2
     State2 = ... -> State3
   within StartState
   ```

2. **Message Passing** (from `CoopSys.csp`):
   ```csp
   Link(1,2) = {| ready, cancel, comp |}
   ```

3. **Composition** (from `RTM_compo.csp`):
   ```csp
   System = Component1 [|msgs|] Buffer [|msgs|] Component2
   ```

4. **Specifications** (from `CoopSys_spec.csp`):
   ```csp
   SafeSpec = Spec_simul(event1, event2, ...)
   ```

5. **Assertions** (from `CoopSys.csp`):
   ```csp
   assert SafeSpec [T= System
   assert System :[deadlock free [F]]
   ```

---

## 🎓 For Your Report

### **What to Include:**

1. **CSP Model**
   - Show your FSM definitions
   - Explain state transitions
   - Document message types

2. **Formal Specifications**
   - Write safety properties in CSP
   - Write liveness properties
   - Explain what each property guarantees

3. **Verification Results**
   - Screenshot of FDR4 showing all checks passed
   - Explain what was verified
   - Discuss any counterexamples found and how you fixed them

4. **Design Decisions**
   - Why Paxos for consensus?
   - How message delays are handled?
   - Timeout values and backoff strategy

5. **Correctness Argument**
   - "Our system is proven deadlock-free by FDR4"
   - "Safety properties verified for all executions"
   - "Design validated before implementation"

---

## 💡 Pro Tips

### **Start Small:**
```
2 robots, 1 gold → verify → works!
4 robots, 2 gold → verify → works!
10 robots, 5 gold → verify → works!
```

### **Test Edge Cases:**
```csp
-- What if both robots propose simultaneously?
-- What if messages arrive out of order?
-- What if partner times out?
-- What if gold disappears while moving to it?
```

### **Use Abstractions:**
```csp
-- Don't model entire 20x20 grid
-- Use symbolic positions: Home, Gold1, Gold2, Deposit
-- Focus on coordination logic, not movement details
```

---

## 🚀 Why This Matters

### **Without CSP:**
```
Code → Test → Bug → Fix → Test → Bug → Fix → ...
```
**Problem:** Can't test all possible interleavings!

### **With CSP:**
```
Model → Verify → Fix model → Verify → Code once correctly
```
**Benefit:** Mathematical proof covers ALL possible executions!

---

## 📚 Files You Have

1. **`CoopSys_CSP/`** - Reference example (cooperative transport robots)
2. **`RobotSystem.csp`** - Your starter template (gold collection robots)
3. **`CSP_VERIFICATION_GUIDE.md`** - Detailed methodology
4. **`HOW_TO_USE_CSP.md`** - This quick start guide

---

## ✅ Action Items

- [ ] Install FDR4
- [ ] Open `CoopSys_CSP/CoopSys.csp` in FDR4
- [ ] Click "Run All" to see verification
- [ ] Study `RoboMng_fsm.csp` to understand FSM structure
- [ ] Open `RobotSystem.csp` (your template)
- [ ] Customize for your specific requirements
- [ ] Run verification in FDR4
- [ ] Fix any counterexamples
- [ ] Once verified → implement in Python with confidence!

---

## 🎯 Bottom Line

**CSP + FDR4 = Mathematical proof your design works**

This is exactly what "formal methods for distributed systems" means in your course!

Use it to:
1. Find bugs in design phase (not coding phase)
2. Prove correctness mathematically
3. Document your system formally
4. Impress in your report with rigorous verification

**Your timing issues with message delays?** 
→ Model them in CSP first
→ Verify they don't break coordination
→ Then implement with confidence!
