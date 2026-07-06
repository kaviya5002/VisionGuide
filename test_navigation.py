import sys
sys.path.insert(0, 'd:\\visionguide')

# Import only the pure functions — no camera, no model, no speech thread
from distance_test import build_navigation_message, get_approx_metres, OBJECT_CONFIG, DIST_ORDER

PASS = 0
FAIL = 0

def check(label, result, must_contain=None, must_be_none=False):
    global PASS, FAIL
    if must_be_none:
        if result is None:
            print(f"  PASS  {label}", flush=True)
            PASS += 1
        else:
            print(f"  FAIL  {label}  got: {result}", flush=True)
            FAIL += 1
        return
    if result is None:
        print(f"  FAIL  {label}  got: None", flush=True)
        FAIL += 1
        return
    if must_contain and must_contain.lower() not in result.lower():
        print(f"  FAIL  {label}  missing '{must_contain}' in: {result}", flush=True)
        FAIL += 1
        return
    print(f"  PASS  {label}  →  {result}", flush=True)
    PASS += 1

print("\n=== Priority filtering ===", flush=True)
check("bottle Far  → silent",   build_navigation_message("bottle","Far","Left",3000),   must_be_none=True)
check("bottle Near → silent",   build_navigation_message("bottle","Near","Left",16000),  must_be_none=True)
check("bottle VN  → speaks",    build_navigation_message("bottle","Very Near","Left",55000), must_contain="Bottle")
check("chair Far  → silent",    build_navigation_message("chair","Far","Center",3000),   must_be_none=True)
check("chair Near → speaks",    build_navigation_message("chair","Near","Center",16000),  must_contain="Chair")
check("person Far → speaks",    build_navigation_message("person","Far","Center",3000),   must_contain="Person")

print("\n=== Direction guidance ===", flush=True)
check("person Center → move left",  build_navigation_message("person","Near","Center",16000), must_contain="left")
check("person Left   → move right", build_navigation_message("person","Near","Left",16000),   must_contain="right")
check("person Right  → move left",  build_navigation_message("person","Near","Right",16000),  must_contain="left")
check("car Left      → move right", build_navigation_message("car","Far","Left",3000),        must_contain="right")
check("bicycle Right → move left",  build_navigation_message("bicycle","Far","Right",3000),   must_contain="left")

print("\n=== Urgency levels ===", flush=True)
check("person Far   → Caution",  build_navigation_message("person","Far","Left",3000),      must_contain="Caution")
check("person Near  → Warning",  build_navigation_message("person","Near","Left",16000),     must_contain="Warning")
check("person VN    → Danger",   build_navigation_message("person","Very Near","Left",55000),must_contain="Danger")
check("chair Near   → Warning",  build_navigation_message("chair","Near","Center",16000),    must_contain="Warning")
check("chair VN     → Danger",   build_navigation_message("chair","Very Near","Center",55000),must_contain="Danger")

print("\n=== Approx distance in metres ===", flush=True)
check("area>120000 → half meter", get_approx_metres(130000), must_contain="half")
check("area 70000  → 1 meter",    get_approx_metres(75000),  must_contain="1 meter")
check("area 20000  → 2 meters",   get_approx_metres(22000),  must_contain="2 meters")
check("area 5000   → 5 meters",   get_approx_metres(6000),   must_contain="5 meters")
check("area 1000   → 5 meters+",  get_approx_metres(1000),   must_contain="5 meters")

print("\n=== Traffic light ===", flush=True)
check("traffic light no frame", build_navigation_message("traffic light","Far","Center",3000,None), must_contain="Traffic")

print("\n=== Example sentences ===", flush=True)
scenarios = [
    ("person",  "Very Near", "Center", 60000),
    ("person",  "Near",      "Left",   20000),
    ("chair",   "Very Near", "Center", 60000),
    ("bicycle", "Far",       "Right",  3000),
    ("car",     "Far",       "Left",   4000),
    ("bottle",  "Very Near", "Right",  60000),
    ("laptop",  "Very Near", "Center", 55000),
]
for name, dist, direction, area in scenarios:
    msg = build_navigation_message(name, dist, direction, area)
    print(f"  {name:12s} {dist:9s} {direction:6s} → {msg}", flush=True)

print(f"\n{'='*50}", flush=True)
print(f"Results: {PASS} passed, {FAIL} failed", flush=True)
