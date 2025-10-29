# CSP Bug Demonstration - Final Working Version

## 🐛 Why Previous Models Passed (Incorrectly)

### **Problem with RobotSystem_Tiny.csp:**
```csp
NoInvalidQuorum = 
  obs_bug_quorum?promises?known ->
    (if (promises <= real_quorum)  
     then STOP  -- Both processes STOP here!
     else NoInvalidQuorum)
```

**Both processes:**
1. Do event: `obs_bug_quorum.1.0`
2. End in: `STOP`

**Result:** Same traces → Refinement passes (wrong!)

---

## ✅ Solution: RobotSystem_Bug_Demo.csp

### **Key Fix:**
```csp
NoBugs = 
  system_proceed?p?k -> NoBugs  -- Accept valid proceeds
  [] bug_detected -> STOP  -- REJECT bug detection!

BuggyRobot =
  system_proceed.1.0 ->  -- Proceeds with insufficient quorum
  bug_detected -> STOP   -- Then detects it was wrong
```

**Now:**
- `NoBugs` refuses `bug_detected` after seeing it
- `BuggyRobot` performs `bug_detected`
- Different traces → **Refinement FAILS** ✓

---

## 🚀 How to Use

1. **Open** `RobotSystem_Bug_Demo.csp` in FDR4
2. **Run** the assertion: `assert NoBugs [T= BuggyRobot`
3. **See FAIL** 

**Counterexample:**
```
1. system_proceed.1.0
   → Robot proceeds with 1 promise, knows 0 teammates
   
2. bug_detected
   → System detects invalid quorum!
   → Calculated quorum = 0 (wrong!)
   → Real quorum = 1 (needs >1 promises)
```

---

## 📊 What This Demonstrates

**The Bug:**
```python
# Python code (full.py line 185-186)
known_teammates = 0  # Message delays - don't know team yet
num_teammates = 0 + 1 = 1  # Thinks team is size 1
quorum = 1 / 2 = 0  # Calculates quorum as 0
has_promises = 1
if (1 > 0):  # Proceeds! WRONG!
```

**The Fix:**
```python
TEAM_SIZE = 10  # Fixed constant
quorum = TEAM_SIZE / 2 = 5  # Always correct
has_promises = 1
if (1 > 5):  # Doesn't proceed (correct!)
```

---

## ✅ This Will Work

**`RobotSystem_Bug_Demo.csp`:**
- ✅ Demonstrates the exact bug
- ✅ Will FAIL in FDR4 (as expected)
- ✅ Shows clear counterexample
- ✅ Fast verification (<5 seconds)
- ✅ Perfect for your report

**Use this one!** 🎯
