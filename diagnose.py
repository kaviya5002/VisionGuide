from distance_test import build_navigation_message, OBJECT_CONFIG, DIST_ORDER
import queue, threading, time

print("=== BUG DIAGNOSIS ===\n", flush=True)

# Simulate exactly what SpeechManager.update() does
# when person(VeryNear) + bottle(VeryNear) + chair(Near) are all stable

stable_names = {"person", "bottle", "chair"}
current_labels = {
    "person" : ("Very Near", 90000, "Center", 100, 50, 400, 400),
    "bottle" : ("Very Near", 55000, "Right",  450, 100, 560, 300),
    "chair"  : ("Near",      20000, "Left",   20,  100, 200, 350),
}

print("--- What build_navigation_message returns for each ---", flush=True)
for name, vals in current_labels.items():
    dist, area, direction, x1, y1, x2, y2 = vals
    msg = build_navigation_message(name, dist, direction, area, None, x1, y1, x2, y2)
    print(f"  {name:12s} {dist:9s} {direction:6s} → {msg}", flush=True)

print("\n--- Simulating sorted order (priority, -area) ---", flush=True)
new_objects = stable_names
for name in sorted(new_objects,
                   key=lambda n: (OBJECT_CONFIG.get(n, {}).get("priority", 3),
                                  -current_labels[n][1])):
    dist, area, direction, x1, y1, x2, y2 = current_labels[name]
    msg = build_navigation_message(name, dist, direction, area, None, x1, y1, x2, y2)
    print(f"  {name:12s} msg={msg}", flush=True)

print("\n--- BUG 1: speech_queue.qsize() == 0 gate ---", flush=True)
print("  All objects build to_speak list correctly.", flush=True)
print("  But speech_queue.put() is only called ONCE with ' '.join(to_speak)", flush=True)
print("  Problem: if person speech is 8 seconds long, bottle+chair", flush=True)
print("  are in to_speak but the SINGLE queue item contains all of them.", flush=True)
print("  That should work... let me check the _known set logic.", flush=True)

print("\n--- BUG 2: _known.add() only happens when msg is not None ---", flush=True)
print("  If bottle returns None (below threshold), it is still added to _known", flush=True)
print("  BUT last_spoken[bottle] = now is set.", flush=True)
print("  Next cooldown check: now - last_spoken[bottle] < COOLDOWN → skip", flush=True)
print("  So bottle gets added to _known but NEVER gets a chance to speak", flush=True)
print("  because its threshold was not met when first seen.", flush=True)
print("  When bottle moves Very Near later, it is already in _known,", flush=True)
print("  and its last_spoken timer hasn't expired yet → SILENT.", flush=True)

print("\n--- BUG 3: queue gate `speech_queue.qsize() == 0` ---", flush=True)
print("  Person speech takes ~4 seconds.", flush=True)
print("  While person is speaking, bottle+chair become stable.", flush=True)
print("  update() is called, to_speak built, but qsize() is 1 → BLOCKED.", flush=True)
print("  By the time queue empties, bottle+chair are already in _known", flush=True)
print("  with last_spoken set → cooldown not expired → NEVER spoken.", flush=True)

print("\n--- BUG 4: cooldown stamped by FIRST WORD of full sentence ---", flush=True)
sentence = "Danger. Person ahead, approximately 1 meter. Move left to avoid immediately. Warning. Chair on your left, approximately 3 meters. Move right."
first_word = sentence.split()[0]
print(f"  Sentence: '{sentence[:60]}...'", flush=True)
print(f"  first_word = '{first_word}'  → stamps last_spoken['Danger'] not 'chair'", flush=True)
print("  So chair cooldown is NEVER stamped → chair re-announces every 7s spam", flush=True)
