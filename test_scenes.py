from distance_test import SceneEngine

engine = SceneEngine()
PASS = 0
FAIL = 0

def check(label, detected, counts, expect_scene, expect_speech=True):
    global PASS, FAIL
    result = engine.infer(set(detected), counts)
    if expect_scene is None:
        ok = result is None
    else:
        ok = result is not None and expect_scene.lower() in result[0].lower()
        if ok and expect_speech:
            ok = result[1] is not None
    status = "PASS" if ok else "FAIL"
    if status == "PASS":
        PASS += 1
    else:
        FAIL += 1
    msg = result[1] if result else None
    print(f"  {status}  {label:35s} -> {result[0] if result else 'None'} | {msg}", flush=True)
    # Reset cooldown for clean test
    engine._last_spoken.clear()

print("\n=== Safety Critical (Priority 0) ===", flush=True)
check("traffic light + car = road crossing",
      ["traffic light","car"], {"traffic light":1,"car":1},
      "ROAD CROSSING")
check("car + truck = heavy traffic",
      ["car","truck"], {"car":1,"truck":1},
      "HEAVY TRAFFIC")
check("stairs = staircase",
      ["stairs","person"], {"stairs":1,"person":1},
      "STAIRCASE")

print("\n=== Important Environment (Priority 1) ===", flush=True)
check("3 persons = busy area",
      ["person"], {"person":3},
      "BUSY AREA")
check("2 persons = NOT busy (below min_count)",
      ["person"], {"person":2},
      None)
check("car alone = roadway",
      ["car"], {"car":1},
      "ROADWAY")
check("person + door = corridor",
      ["person","door"], {"person":1,"door":1},
      "CORRIDOR")
check("person + bench = corridor",
      ["person","bench"], {"person":1,"bench":1},
      "CORRIDOR")

print("\n=== Contextual Indoor (Priority 2) ===", flush=True)
check("dining table + chair = dining area",
      ["dining table","chair"], {"dining table":1,"chair":1},
      "DINING AREA")
check("dining table + cup = dining area",
      ["dining table","cup"], {"dining table":1,"cup":1},
      "DINING AREA")
check("laptop + keyboard = workspace",
      ["laptop","keyboard"], {"laptop":1,"keyboard":1},
      "WORKSPACE")
check("couch + tv = living room",
      ["couch","tv"], {"couch":1,"tv":1},
      "LIVING ROOM")
check("chair + person = seating area",
      ["chair","person"], {"chair":1,"person":1},
      "SEATING AREA")
check("bed = bedroom",
      ["bed"], {"bed":1},
      "BEDROOM")

print("\n=== No match ===", flush=True)
check("bottle alone = no scene",
      ["bottle"], {"bottle":1},
      None)
check("empty = no scene",
      [], {},
      None)

print("\n=== Cooldown (same scene should not repeat) ===", flush=True)
engine._last_spoken.clear()
r1 = engine.infer({"car","truck"}, {"car":1,"truck":1})
r2 = engine.infer({"car","truck"}, {"car":1,"truck":1})  # still in cooldown
spoke_twice = r1 is not None and r2 is not None and r2[1] is None
print(f"  {'PASS' if spoke_twice else 'FAIL'}  Second call returns display but no speech (cooldown)", flush=True)
if spoke_twice: PASS += 1
else: FAIL += 1

print(f"\n{'='*55}", flush=True)
print(f"Results: {PASS} passed, {FAIL} failed", flush=True)
