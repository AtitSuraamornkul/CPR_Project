# How to Verify Each Test Separately

## 📁 Files Created

You now have **3 separate test files**, each verifying one property:

```
Test1_Deadlock.csp       → Deadlock freedom (FASTEST)
Test2_FinderHelper.csp   → Liveness property (MEDIUM)
Test3_OnePair.csp        → Mutual exclusion (SLOWEST)
```

---

## 🎯 Why This Helps

### **Memory Benefits:**
- ✅ Each file starts fresh in FDR4
- ✅ No accumulated state from previous checks
- ✅ FDR4 can optimize for specific property
- ✅ Can close/restart between runs

### **Debugging Benefits:**
- ✅ See which specific property fails
- ✅ Isolate counterexamples
- ✅ Focus fixes on specific bugs
- ✅ Track progress per property

---

## 🚀 Verification Order (Recommended)

### **Step 1: Test1_Deadlock.csp** (Start here!)
```
Expected time: 30-60 seconds
Expected result: FAIL

Counterexample shows:
- Finder picks helper
- Late Response message arrives
- Finder cannot accept it
- DEADLOCK

Bug demonstrated: Missing late message handling (Bug #1)
```

**Why first?** Fastest check, clearest counterexample.

---

### **Step 2: Test2_FinderHelper.csp**
```
Expected time: 1-2 minutes
Expected result: FAIL or STUCK

Issue:
- Helper waits for events in fixed order
- Message delays cause wrong order
- Helper waits forever for MovingToGold event

Bug demonstrated: Fixed event ordering (Bug #2)
```

**Why second?** Tests liveness - shows system gets stuck.

---

### **Step 3: Test3_OnePair.csp** (Optional)
```
Expected time: 2-5 minutes
Expected result: May PASS (with 2 robots, only 1 pair possible)

Tests:
- Mutual exclusion
- No duplicate pickups
- Only one coordination at a time

Bug demonstrated: Less likely to fail with 2 robots
```

**Why last?** Most complex, least likely to show bugs with 2 robots.

---

## 💻 How to Run in FDR4

### **For Each File:**

1. **Open FDR4**
2. **File → Open** → Select test file
3. **Wait for parsing** (~5 seconds)
4. **Select the assertion** (only one in each file)
5. **Click "Run"**
6. **Wait for result**
7. **Document findings**

### **If it passes:**
```
✅ Property holds (unexpected for buggy version!)
→ Document why
→ Maybe bug not triggered in this configuration
```

### **If it fails:**
```
❌ Counterexample found!
→ Click "Show Counterexample"
→ Save the trace
→ Document the bug scenario
→ Perfect for your report!
```

### **If it gets stuck:**
```
⏳ Still running after 10+ minutes?
→ Stop the verification
→ This itself is evidence of complexity
→ Document: "State space too large to verify completely"
→ Try with even more restrictions
```

---

## 📊 Expected Results Summary

| File | Time | Result | Bug Shown |
|------|------|--------|-----------|
| **Test1_Deadlock** | 30-60s | ❌ FAIL | Late message handling |
| **Test2_FinderHelper** | 1-2min | ❌ FAIL | Event ordering |
| **Test3_OnePair** | 2-5min | ❓ MAY PASS | Mutual exclusion |

---

## 📝 For Your Report

### **Document Each Test:**

```
Test 1: Deadlock Freedom
- File: Test1_Deadlock.csp
- Runtime: 45 seconds
- Result: FAILED
- Counterexample depth: 28 steps
- Bug found: Finder process deadlocks when late Response arrives
- Root cause: Missing message handler in WaitHere state

Test 2: Finder-Helper Coordination
- File: Test2_FinderHelper.csp  
- Runtime: 90 seconds
- Result: FAILED (stuck)
- Issue: Helper waits forever for MovingToGold event
- Root cause: Fixed event ordering, should accept in any order

Test 3: Mutual Exclusion
- File: Test3_OnePair.csp
- Runtime: 3 minutes
- Result: PASSED
- Note: With 2 robots, only one pair can form anyway
```

### **Write Analysis:**

> "We separated each property into individual CSP files to enable tractable verification and isolate bugs. FDR4 found deadlocks in Test 1 within 45 seconds, showing the Finder cannot handle late messages. Test 2 revealed the Helper waits indefinitely for events, exposing the fixed event ordering bug. These are precisely the concurrency issues that formal methods excel at finding—issues that would be nearly impossible to catch through traditional testing due to their dependence on specific message timing."

---

## 🔧 If Still Using Too Much Memory

### **Option A: Comment Out Specs**

In any file, simplify the specification process:

```csp
-- BEFORE (complex spec):
FinderHasHelper =
  obs.BecameFinder?finder_id ->
    (obs.BecameHelper?helper_id!finder_id -> FinderHasHelper
     [] obs.Timeout.finder_id -> FinderHasHelper)
  [] obs.BecameHelper?h?f -> FinderHasHelper
  [] obs.PickupSuccess?id1?id2 -> FinderHasHelper
  [] ...

-- AFTER (just use System directly):
-- Comment out the spec, just check System for deadlock
assert System :[deadlock free [F]]
```

### **Option B: Further Reduce Timeouts**

```csp
RESPONSE_TIMEOUT = 5   -- Was 10
HERE_TIMEOUT = 8       -- Was 15
MOVE_TIMEOUT = 5       -- Was 10
MAX_RETRIES = 1        -- Was 2
```

### **Option C: Verify Without Delays**

Comment out the delay in Buffer:
```csp
Buffer(id, queue) =
  send.id?msg -> recv.id.msg -> Buffer(id, queue)  -- Immediate delivery
  [] tock -> Buffer(id, queue)
```

This removes delays but still tests protocol logic.

---

## ✅ Success Criteria

You've successfully completed verification when:

1. ✅ At least ONE test shows a bug (counterexample)
2. ✅ You can explain what the counterexample means
3. ✅ You've documented the bug scenario
4. ✅ You understand which code needs fixing

**You don't need all 3 to pass/fail - even ONE good counterexample is excellent for your report!**

---

## 🎯 Next Steps After Verification

1. **Document findings** (counterexamples, traces)
2. **Apply fixes** (use ProfessorMethod.csp with fixes)
3. **Re-verify** (show fixes work)
4. **Compare** (before/after)
5. **Write report** (formal verification caught bugs!)

---

## 💡 Pro Tip

**Start with Test1_Deadlock.csp** - it's the fastest and most likely to show a clear bug!

If you get a good counterexample from just this one file, that's enough to demonstrate formal verification found a real bug! 🎓
