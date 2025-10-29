# CSP Verification Checklist

## ✅ Step-by-Step Guide

### **Phase 1: Initial Verification (Find Bugs)**

- [ ] Install FDR4 from https://cocotec.io/fdr/
- [ ] Open `RobotSystem_Simple.csp` in FDR4
- [ ] Click "Run All" to check all assertions
- [ ] Document which assertions FAIL (expected: 3-4 failures)

**For each failure:**
- [ ] Click "View Counterexample" 
- [ ] Copy the trace to a document
- [ ] Analyze: What sequence of events led to the bug?
- [ ] Identify: Which line in Python `full.py` has this bug?
- [ ] Document in report: "Bug X found by FDR4"

**Expected bugs to find:**
- [ ] Bug 1: Invalid quorum (robot proceeds with insufficient promises)
- [ ] Bug 2: No Paxos timeout (robot stuck in preparing state)
- [ ] Bug 3: Partner timeout too short (coordination fails)
- [ ] Bug 4: Race conditions (multiple plans committed)

---

### **Phase 2: Fix Design in CSP**

**Fix 1: Correct Quorum Calculation**
- [ ] Edit `RobotSystem_Simple.csp`
- [ ] Find line: `num_teammates = #known_teammates + 1`
- [ ] Replace with: `quorum = TEAM_SIZE / 2`
- [ ] Re-run assertion: `NoInvalidQuorum`
- [ ] Verify: ✅ Should now PASS

**Fix 2: Add Paxos Timeout**
- [ ] Add timeout counter to `RobotPreparing` state
- [ ] Add timeout check after N tocks
- [ ] Add transition: timeout → back to Idle with backoff
- [ ] Re-run assertion: `Deadlock free`
- [ ] Verify: ✅ Should now PASS

**Fix 3: Extend Partner Timeout**
- [ ] Change: `PARTNER_TIMEOUT = 10` to `PARTNER_TIMEOUT = 30`
- [ ] Re-run assertion: `MinimalTimeouts`
- [ ] Verify: ✅ Should now PASS

**Fix 4: Better Proposal Conflict Detection**
- [ ] Add check for higher proposal IDs
- [ ] Reject lower proposals
- [ ] Re-run assertion: `OnePlanPerRound`
- [ ] Verify: ✅ Should now PASS

**Final Check:**
- [ ] Run ALL assertions
- [ ] All should pass: ✅ ✅ ✅ ✅
- [ ] Document states explored and verification time
- [ ] Screenshot FDR4 results for report

---

### **Phase 3: Implement Verified Design in Python**

**Create new file: `full_verified.py`**

**Fix 1: Quorum Calculation**
- [ ] Add constant: `TEAM_SIZE = 10`
- [ ] Replace line 185-186:
  ```python
  # OLD:
  num_teammates = len(self.teammate_states) + 1
  if len(self.promises_received) > num_teammates / 2:
  
  # NEW:
  TEAM_SIZE = 10  # Constant at top of class
  if len(self.promises_received) > TEAM_SIZE / 2:
  ```

**Fix 2: Paxos Timeout**
- [ ] Add to `__init__`: `self.paxos_timeout = 0`
- [ ] Add in `process_messages` after handling promises:
  ```python
  elif msg_type == "paxos_promise":
      if self.paxos_state == 'preparing':
          self.paxos_timeout = 0  # Reset on message
          # ... existing logic ...
  ```
- [ ] Add in `decide_action`:
  ```python
  if self.paxos_state == 'preparing':
      self.paxos_timeout += 1
      if self.paxos_timeout > 30:  # Timeout after 30 steps
          self.paxos_state = 'idle'
          self.proposal_backoff = random.randint(5, 15)
          self.promises_received = set()
  ```

**Fix 3: Partner Timeout**
- [ ] Change line 302:
  ```python
  # OLD:
  if self.wait_timer > 20:
  
  # NEW:
  MAX_PARTNER_WAIT = 50  # Longer timeout
  if self.wait_timer > MAX_PARTNER_WAIT:
  ```

**Fix 4: Conflict Detection**
- [ ] Add in `decide_action` when receiving plan:
  ```python
  if self.current_plan and self.id in self.current_plan:
      # Check if already has assignment
      if self.state != "idle":
          return "idle"  # Ignore conflicting plan
  ```

---

### **Phase 4: Testing & Comparison**

**Test Original Implementation**
- [ ] Run `python full.py` (with delays)
- [ ] Record metrics:
  - [ ] Pickups succeeded: ___
  - [ ] Pickups failed: ___
  - [ ] Robots stuck in preparing: ___
  - [ ] Partner timeouts: ___
  - [ ] Time to complete: ___
  - [ ] Efficiency: ___%

**Test Verified Implementation**
- [ ] Run `python full_verified.py` (with delays)
- [ ] Record same metrics:
  - [ ] Pickups succeeded: ___
  - [ ] Pickups failed: ___
  - [ ] Robots stuck in preparing: ___
  - [ ] Partner timeouts: ___
  - [ ] Time to complete: ___
  - [ ] Efficiency: ___%

**Compare Results**
- [ ] Create comparison table
- [ ] Show improvement in efficiency
- [ ] Show reduction in failures
- [ ] Include in report

---

### **Phase 5: Report Writing**

**Section 1: Problem Description**
- [ ] Describe multi-robot coordination challenge
- [ ] Explain message delay problem
- [ ] State goals: consensus + coordination with delays

**Section 2: Initial Design**
- [ ] Show Python implementation approach
- [ ] Explain Paxos protocol choice
- [ ] Describe state machine design

**Section 3: Formal Modeling**
- [ ] Show simplified CSP model
- [ ] Explain abstractions (3 robots, symbolic positions)
- [ ] Justify why abstractions are valid
- [ ] Show key FSM definitions

**Section 4: Initial Verification Results**
- [ ] Show FDR4 failures
- [ ] Include counterexample traces
- [ ] Explain each bug found:
  - [ ] What the bug is
  - [ ] Why it occurs
  - [ ] What property it violates
- [ ] Include screenshots of failed assertions

**Section 5: Design Refinement**
- [ ] Show iterative fixes in CSP
- [ ] Explain reasoning for each fix
- [ ] Show modified FSM transitions
- [ ] Document verification after each fix

**Section 6: Final Verification**
- [ ] Show all assertions passing ✅
- [ ] Include FDR4 screenshot
- [ ] State: "System proven correct"
- [ ] Mention states explored, verification time

**Section 7: Implementation**
- [ ] Show key Python code changes
- [ ] Explain how CSP design translates to code
- [ ] Highlight correspondence between CSP and Python

**Section 8: Experimental Results**
- [ ] Comparison table (before vs after)
- [ ] Graphs showing improvement
- [ ] Analysis of results

**Section 9: Discussion**
- [ ] Value of formal verification
- [ ] Bugs found systematically vs trial-and-error
- [ ] Confidence in correctness
- [ ] Lessons learned

**Section 10: Conclusion**
- [ ] Summary of approach
- [ ] Successful verification and implementation
- [ ] Formal methods demonstrate mastery of course concepts

---

## 📊 Expected Timeline

| Phase | Time Estimate |
|-------|--------------|
| Phase 1: Initial verification | 2-3 hours |
| Phase 2: Fix CSP model | 4-6 hours |
| Phase 3: Implement fixes | 3-4 hours |
| Phase 4: Testing | 2-3 hours |
| Phase 5: Report writing | 8-10 hours |
| **Total** | **19-26 hours** |

---

## 🎯 Success Criteria

### **Verification Success:**
- [ ] All CSP assertions pass in FDR4
- [ ] Counterexamples documented for all bugs
- [ ] Clear explanation of each fix

### **Implementation Success:**
- [ ] Verified version runs without deadlocks
- [ ] 50%+ improvement in efficiency
- [ ] Significant reduction in failures
- [ ] All gold eventually collected

### **Report Success:**
- [ ] Clear narrative: problem → model → verify → fix → implement
- [ ] Formal specifications properly written
- [ ] Counterexamples properly analyzed
- [ ] Results show improvement
- [ ] Demonstrates mastery of formal methods

---

## 💡 Tips

**Verification:**
- Start with simplest fix first (quorum calculation)
- Fix one bug at a time, verify after each
- If FDR4 takes >5 minutes, model is too complex (simplify more)

**Implementation:**
- Create new file, don't modify original (for comparison)
- Test after each fix to ensure it works
- Keep old version for before/after comparison

**Report:**
- Use screenshots liberally (especially FDR4 results)
- Show actual counterexample traces (not just descriptions)
- Make clear connection between CSP model and Python code
- Emphasize: "Bugs found by formal verification, not testing"

---

## 🚀 Ready to Start?

1. ✅ Install FDR4
2. ✅ Open `RobotSystem_Simple.csp`
3. ✅ Click "Run All"
4. ✅ Document failures
5. ✅ Start fixing!

Good luck! This approach will result in a strong demonstration of formal methods mastery. 🎓
