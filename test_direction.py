def get_direction(cx, fw):
    t = fw / 3
    return 'Left' if cx < t else 'Center' if cx < 2*t else 'Right'

fw = 640
tests = [
    (0,   'Left'),
    (100, 'Left'),
    (213, 'Left'),
    (214, 'Center'),
    (320, 'Center'),
    (426, 'Center'),
    (427, 'Right'),
    (639, 'Right'),
]

all_pass = True
for cx, expected in tests:
    result = get_direction(cx, fw)
    status = 'PASS' if result == expected else 'FAIL'
    if status == 'FAIL':
        all_pass = False
    print(f"  cx={cx:3d}  expected={expected:6s}  got={result:6s}  {status}", flush=True)

print(f"\nAll direction tests passed: {all_pass}", flush=True)

# Simulate full label format
examples = [
    ("person",    "Near",      "Left"),
    ("bottle",    "Far",       "Right"),
    ("chair",     "Very Near", "Center"),
    ("cell phone","Far",       "Right"),
    ("laptop",    "Near",      "Center"),
]
print("\nLabel format preview:", flush=True)
for name, dist, direction in examples:
    screen_label = f"{name} - {dist} - {direction}"
    speech_text  = f"{name} {dist} {direction}"
    print(f"  Screen : {screen_label}", flush=True)
    print(f"  Speech : {speech_text}", flush=True)
