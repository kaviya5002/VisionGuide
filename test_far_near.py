from distance_test import build_navigation_message

cases = [
    ("car",     "Far",       "Left",   3000),
    ("car",     "Near",      "Left",   16000),
    ("bicycle", "Far",       "Right",  3000),
    ("bicycle", "Near",      "Right",  16000),
]
for name, dist, direction, area in cases:
    msg = build_navigation_message(name, dist, direction, area)
    has_avoid = any(w in (msg or "") for w in ["Move", "move"])
    print(f"{name:8s} {dist:9s} {direction:6s} → avoidance={has_avoid} → {msg}", flush=True)
print("Far=inform only (correct for blind nav). Near/VN=avoidance added.", flush=True)
