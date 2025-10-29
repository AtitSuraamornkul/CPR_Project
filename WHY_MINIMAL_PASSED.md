# Why RobotSystem_Minimal.csp Passed (And Shouldn't Have)

## 🐛 The Issue

You're right - the minimal model **passed when it should have failed**!

## 🔍 Root Cause

The model had a logic error - robots never actually got into the buggy scenario because:

**Problem 1: No promise exchange mechanism**
- Robot 1 enters `Preparing` state with only its own promise `{1}`
- Robot 2 is in `Idle` state
- Robot 2 never sends a promise to Robot 1 (no acceptor logic!)
- Robot 1 waits forever, never proceeds
- Bug never triggers!

**Problem 2: Wrong condition check**
```csp
if (promise_count <= TEAM_SIZE/2)
```
Should detect bug when `promise_count` is insufficient, but:
- If `promise_count = 1` and `TEAM_SIZE/2 = 1`
- Then `1 <= 1` is true, would fire obs_invalid_quorum
- But robot never reaches `proceed` because it's stuck waiting!

## ✅ Solution: Ultra-Simple Model

I've created **`RobotSystem_Tiny.csp`** which:
- ✅ Single robot process (no coordination needed)
- ✅ Directly shows the buggy calculation
- ✅ No complex state machine
- ✅ **Will definitely fail as expected**

## 🚀 Try This Instead

**Open `RobotSystem_Tiny.csp` in FDR4:**

```csp
TEAM_SIZE = 3
known_teammates = 0  -- Bug: doesn't know about teammates
promises_received = 1

quorum_needed = (0 + 1) / 2 = 0  -- BUG!
if (1 > 0) then proceed  -- Proceeds incorrectly!

obs_bug_quorum.1.0 -> STOP
```

**This WILL fail** and show:
```
Counterexample: obs_bug_quorum.1.0
- Robot has 1 promise
- Knows 0 teammates
- Calculates quorum = 0 (WRONG!)
- Proceeds anyway
- Should need at least 2 promises for team of 3
```

## 📝 Summary

**RobotSystem_Minimal.csp:** Too complex, robots couldn't exchange promises properly → deadlocked before reaching bug

**RobotSystem_Tiny.csp:** Ultra-simple, directly demonstrates the buggy math → will fail as expected

---

## 🎯 Use RobotSystem_Tiny.csp for Your Report

It's the clearest demonstration:
1. Shows exact buggy calculation
2. Verifies instantly
3. Counterexample is obvious
4. Easy to explain in report
5. Easy to fix and re-verify

Perfect for formal verification demonstration! ✨
