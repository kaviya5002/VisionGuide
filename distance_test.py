from ultralytics import YOLO
import cv2
import win32com.client
import pythoncom
import time
import threading
import queue
from collections import deque

# ── Constants ──────────────────────────────────────────────────────────────────
MODEL_PATH     = "yolov8x.pt"
CONF           = 0.35
IOU            = 0.45
IMG_SIZE       = 640
FRAME_W        = 640
FRAME_H        = 480
CONFIRM_FRAMES = 3
COOLDOWN       = 7             # seconds before repeating same object

# ── Object configuration ───────────────────────────────────────────────────────
# priority : 0 = high (announce at any distance)
#            1 = medium (announce Near + Very Near)
#            2 = low (announce Very Near only)
# speak_at  : minimum distance tier required to trigger speech
# label     : friendly name used in spoken sentence
OBJECT_CONFIG = {
    # ── Tier 0 — immediate hazards ─────────────────────────────────────────
    "person"      : {"priority": 0, "speak_at": "Far",      "label": "Person"},
    "car"         : {"priority": 0, "speak_at": "Far",      "label": "Vehicle"},
    "truck"       : {"priority": 0, "speak_at": "Far",      "label": "Truck"},
    "bus"         : {"priority": 0, "speak_at": "Far",      "label": "Bus"},
    "motorcycle"  : {"priority": 0, "speak_at": "Far",      "label": "Motorcycle"},
    "bicycle"     : {"priority": 0, "speak_at": "Far",      "label": "Bicycle"},
    "traffic light": {"priority": 0, "speak_at": "Far",     "label": "Traffic light"},
    # ── Tier 1 — obstacles ─────────────────────────────────────────────────
    "chair"       : {"priority": 1, "speak_at": "Near",     "label": "Chair"},
    "couch"       : {"priority": 1, "speak_at": "Near",     "label": "Couch"},
    "dining table": {"priority": 1, "speak_at": "Near",     "label": "Table"},
    "bed"         : {"priority": 1, "speak_at": "Near",     "label": "Bed"},
    "bench"       : {"priority": 1, "speak_at": "Near",     "label": "Bench"},
    "door"        : {"priority": 1, "speak_at": "Near",     "label": "Door"},
    "stairs"      : {"priority": 1, "speak_at": "Near",     "label": "Stairs"},
    # ── Tier 2 — low-priority context objects ──────────────────────────────
    "bottle"      : {"priority": 2, "speak_at": "Very Near","label": "Bottle"},
    "cup"         : {"priority": 2, "speak_at": "Very Near","label": "Cup"},
    "cell phone"  : {"priority": 2, "speak_at": "Very Near","label": "Cell phone"},
    "laptop"      : {"priority": 2, "speak_at": "Very Near","label": "Laptop"},
    "mouse"       : {"priority": 2, "speak_at": "Very Near","label": "Mouse"},
    "keyboard"    : {"priority": 2, "speak_at": "Very Near","label": "Keyboard"},
    "backpack"    : {"priority": 2, "speak_at": "Very Near","label": "Backpack"},
    "handbag"     : {"priority": 2, "speak_at": "Very Near","label": "Handbag"},
    "suitcase"    : {"priority": 2, "speak_at": "Very Near","label": "Suitcase"},
    "book"        : {"priority": 2, "speak_at": "Very Near","label": "Book"},
    "scissors"    : {"priority": 2, "speak_at": "Very Near","label": "Scissors"},
    "bowl"        : {"priority": 2, "speak_at": "Very Near","label": "Bowl"},
    "remote"      : {"priority": 2, "speak_at": "Very Near","label": "Remote"},
    "tv"          : {"priority": 2, "speak_at": "Very Near","label": "Screen"},
    "clock"       : {"priority": 2, "speak_at": "Very Near","label": "Clock"},
}

# Distance tier ordering for threshold comparisons
DIST_ORDER = {"Far": 0, "Near": 1, "Very Near": 2}

# ══════════════════════════════════════════════════════════════════════════════
#  SCENE RULES
#  Each rule defines what combination of detected objects implies an environment.
#  priority : 0 = safety-critical (road/stairs), 1 = important, 2 = contextual
#  requires : ALL of these must be in detected set
#  any_of   : at least ONE of these must also be present (optional filter)
#  message  : spoken announcement
#  display  : short label shown on screen overlay
# ══════════════════════════════════════════════════════════════════════════════
SCENE_RULES = [
    # ── Priority 0 — Safety critical ──────────────────────────────────────
    {
        "name"    : "road_crossing",
        "priority": 0,
        "requires": {"traffic light"},
        "any_of"  : {"car", "truck", "bus", "motorcycle", "bicycle"},
        "message" : "Caution. You are near a road crossing. Vehicles are present.",
        "display" : "ROAD CROSSING",
    },
    {
        "name"    : "heavy_traffic",
        "priority": 0,
        "requires": {"car", "truck"},
        "any_of"  : None,
        "message" : "Warning. Heavy traffic detected ahead. Stay on the pavement.",
        "display" : "HEAVY TRAFFIC",
    },
    {
        "name"    : "staircase",
        "priority": 0,
        "requires": {"stairs"},
        "any_of"  : None,
        "message" : "Caution. A staircase is nearby. Move carefully.",
        "display" : "STAIRCASE NEARBY",
    },
    # ── Priority 1 — Important environment ────────────────────────────────
    {
        "name"    : "busy_pedestrian_area",
        "priority": 1,
        "requires": set(),
        "any_of"  : {"person"},
        "min_count": 3,          # needs 3+ persons detected simultaneously
        "message" : "Busy area ahead. Multiple people detected. Proceed carefully.",
        "display" : "BUSY AREA",
    },
    {
        "name"    : "road_scene",
        "priority": 1,
        "requires": set(),
        "any_of"  : {"car", "truck", "bus", "motorcycle"},
        "message" : "You appear to be near a roadway. Stay alert.",
        "display" : "ROADWAY",
    },
    {
        "name"    : "corridor",
        "priority": 1,
        "requires": {"person"},
        "any_of"  : {"door", "bench"},
        "message" : "You appear to be in a corridor or hallway.",
        "display" : "CORRIDOR",
    },
    # ── Priority 2 — Contextual indoor scenes ─────────────────────────────
    {
        "name"    : "dining_area",
        "priority": 2,
        "requires": {"dining table"},
        "any_of"  : {"chair", "cup", "bowl", "bottle"},
        "message" : "Indoor dining area detected.",
        "display" : "DINING AREA",
    },
    {
        "name"    : "office_workspace",
        "priority": 2,
        "requires": {"laptop"},
        "any_of"  : {"chair", "keyboard", "mouse", "book"},
        "message" : "Office or workspace area detected.",
        "display" : "WORKSPACE",
    },
    {
        "name"    : "living_room",
        "priority": 2,
        "requires": {"couch"},
        "any_of"  : {"tv", "remote", "chair", "person"},
        "message" : "Living room or seating area detected.",
        "display" : "LIVING ROOM",
    },
    {
        "name"    : "seating_area",
        "priority": 2,
        "requires": {"chair"},
        "any_of"  : {"dining table", "person", "cup", "bottle"},
        "message" : "Indoor seating area detected.",
        "display" : "SEATING AREA",
    },
    {
        "name"    : "bedroom",
        "priority": 2,
        "requires": {"bed"},
        "any_of"  : None,
        "message" : "Bedroom area detected.",
        "display" : "BEDROOM",
    },
]

SCENE_COOLDOWN = 20   # seconds before repeating same scene announcement

# ── Scene Engine ───────────────────────────────────────────────────────────────
class SceneEngine:
    """
    Analyses the full set of detected object names and infers
    the surrounding environment. Returns one scene message per
    SCENE_COOLDOWN window, highest priority first.
    """
    def __init__(self):
        self._last_spoken  = {}   # {scene_name: timestamp}
        self._current      = None # scene name currently displayed on screen

    def infer(self, detected_names: set, object_counts: dict) -> tuple[str,str] | None:
        """
        detected_names : set of all stable object class names this frame
        object_counts  : {name: count} how many instances of each object
        Returns (display_text, speech_message) or None.
        """
        now = time.time()

        for rule in sorted(SCENE_RULES, key=lambda r: r["priority"]):
            requires = rule.get("requires", set())
            any_of   = rule.get("any_of",   None)
            min_count= rule.get("min_count", 1)

            # Check requires — all must be present
            if requires and not requires.issubset(detected_names):
                continue

            # Check any_of — at least one must be present
            if any_of and not (any_of & detected_names):
                continue

            # Check min_count — for crowd detection
            if min_count > 1:
                trigger_obj = list(rule.get("any_of", set()))[0]
                if object_counts.get(trigger_obj, 0) < min_count:
                    continue

            scene_name = rule["name"]
            self._current = rule["display"]

            # Check cooldown — only speak if enough time has passed
            if now - self._last_spoken.get(scene_name, 0) > SCENE_COOLDOWN:
                self._last_spoken[scene_name] = now
                print(f"[SCENE] {scene_name} — {rule['message']}", flush=True)
                return (rule["display"], rule["message"])

            # Scene matches but still in cooldown — just update display, no speech
            return (rule["display"], None)

        self._current = None
        return None

    @property
    def current_display(self) -> str | None:
        return self._current

# ── Direction helper ───────────────────────────────────────────────────────────
def get_direction(cx: int, frame_width: int) -> str:
    third = frame_width / 3
    if cx < third:
        return "Left"
    elif cx < 2 * third:
        return "Center"
    else:
        return "Right"

# ── Approximate distance in metres (area-based, honest estimate) ───────────────
def get_approx_metres(area: int) -> str:
    # Calibrated for 640x480 webcam, typical object sizes
    if area > 120000: return "less than half a meter"
    if area > 70000:  return "approximately 1 meter"
    if area > 40000:  return "approximately 1 and a half meters"
    if area > 20000:  return "approximately 2 meters"
    if area > 10000:  return "approximately 3 meters"
    if area > 5000:   return "approximately 5 meters"
    return "more than 5 meters away"

# ── Traffic light colour detection ────────────────────────────────────────────
def detect_traffic_light_colour(frame, x1: int, y1: int, x2: int, y2: int) -> str:
    """
    Crop the traffic light bounding box, convert to HSV,
    and return 'red', 'green', 'yellow', or 'unknown'.
    """
    crop = frame[max(0,y1):y2, max(0,x1):x2]
    if crop.size == 0:
        return "unknown"

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    # Red wraps around 0/180 in HSV
    red_mask   = (cv2.inRange(hsv, (0,  120, 70), (10, 255, 255)) +
                  cv2.inRange(hsv, (170,120, 70), (180,255, 255)))
    green_mask  = cv2.inRange(hsv, (40, 80, 70),  (90, 255, 255))
    yellow_mask = cv2.inRange(hsv, (20, 100, 100),(35, 255, 255))

    counts = {
        "red"   : int(cv2.countNonZero(red_mask)),
        "green" : int(cv2.countNonZero(green_mask)),
        "yellow": int(cv2.countNonZero(yellow_mask)),
    }
    best = max(counts, key=counts.get)
    return best if counts[best] > 30 else "unknown"

# ── Navigation decision engine ─────────────────────────────────────────────────
def build_navigation_message(name: str, dist: str, direction: str,
                              area: int, frame=None,
                              x1: int = 0, y1: int = 0,
                              x2: int = 0, y2: int = 0) -> str | None:
    """
    Returns a complete spoken navigation instruction, or None if the object
    does not meet the minimum distance threshold for its priority tier.
    """
    cfg = OBJECT_CONFIG.get(name)
    if cfg is None:
        # Unknown object — only speak very near
        if dist != "Very Near":
            return None
        return f"Unknown object {direction.lower()}. Be careful."

    # Check if this object meets its minimum distance threshold
    if DIST_ORDER[dist] < DIST_ORDER[cfg["speak_at"]]:
        return None   # too far away for this tier — stay silent

    label = cfg["label"]
    metres = get_approx_metres(area)

    # ── Traffic light — pedestrian logic ──────────────────────────────────
    # Red   = vehicles stopped   → safe for pedestrian to cross
    # Green = vehicles moving    → pedestrian must stop and wait
    # Yellow= vehicles slowing   → pedestrian should wait, do not cross
    if name == "traffic light":
        colour = "unknown"
        if frame is not None:
            colour = detect_traffic_light_colour(frame, x1, y1, x2, y2)
        if colour == "red":
            return "Signal is red. Vehicles are stopped. You may cross safely."
        elif colour == "green":
            return "Signal is green. Vehicles are moving. Please stop and wait."
        elif colour == "yellow":
            return "Signal is yellow. Vehicles are slowing down. Wait. Do not cross."
        else:
            return f"Traffic light detected {direction.lower()}. Proceed with caution."

    # ── Avoidance instruction based on direction ───────────────────────────
    if direction == "Left":
        avoid = "Move right."
    elif direction == "Right":
        avoid = "Move left."
    else:  # Center
        avoid = "Move left to avoid."   # default safe side for center objects

    # ── Direction phrase ───────────────────────────────────────────────────
    dir_phrase = {
        "Left"  : "on your left",
        "Right" : "on your right",
        "Center": "ahead",
    }[direction]

    # ── Urgency prefix based on distance ──────────────────────────────────
    if dist == "Very Near":
        urgency = "Danger."
        action  = avoid.replace(".", " immediately.")
    elif dist == "Near":
        urgency = "Warning."
        action  = avoid
    else:  # Far
        urgency = "Caution."
        action  = ""   # just inform, no avoidance instruction at Far

    # ── Assemble final message ─────────────────────────────────────────────
    if dist == "Far":
        return f"{urgency} {label} {dir_phrase}, {metres}."
    else:
        return f"{urgency} {label} {dir_phrase}, {metres}. {action}"

# ── Model ──────────────────────────────────────────────────────────────────────
print("Loading yolov8x...", flush=True)
model = YOLO(MODEL_PATH)
print(f"Model ready — {len(model.names)} classes", flush=True)

# ── Camera ─────────────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("ERROR: Camera failed to open", flush=True)
    exit(1)

print("Camera ready", flush=True)

# ══════════════════════════════════════════════════════════════════════════════
#  SPEECH MANAGER  (architecture unchanged — only message content changes)
#  — win32com SAPI5 owns its own thread (COM apartment rule)
#  — Lock released before queue.put() — zero deadlock
#  — _known tracks visible objects, reappearance re-triggers speech
#  — Cooldown stamped after Speak() finishes
# ══════════════════════════════════════════════════════════════════════════════
class SpeechManager:
    def __init__(self):
        self._queue       = queue.Queue()
        self._known       = set()          # objects currently visible + announced
        self._pending     = set()          # objects seen but below threshold, not yet spoken
        self._last_spoken = {}             # {name: time speech finished}
        self._lock        = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        pythoncom.CoInitialize()
        sapi = win32com.client.Dispatch("SAPI.SpVoice")
        sapi.Rate = -2
        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                print(f"[SPEECH] {text}", flush=True)
                sapi.Speak(text)
            except Exception as e:
                print(f"[SPEECH ERROR] {e}", flush=True)
            finally:
                # BUG 4 FIX: stamp each object name individually, not first word of sentence
                # Sentence format is "Msg1. Msg2." — extract names from current_labels
                # We pass names via a side-channel attribute set before queue.put()
                with self._lock:
                    now = time.time()
                    for name in getattr(self, '_pending_stamp', []):
                        self._last_spoken[name] = now
                    self._pending_stamp = []
                self._queue.task_done()
        pythoncom.CoUninitialize()

    def update(self, stable_names: set, current_labels: dict, latest_frame):
        now      = time.time()
        to_speak = []
        spoken_names = []

        with self._lock:
            # Objects that left frame — remove from known AND pending so reappearance re-triggers
            gone = self._known - stable_names
            self._known   -= gone
            self._pending -= gone

            new_objects = stable_names - self._known - self._pending

            # ── New objects (never seen before this session) ───────────────────
            for name in sorted(new_objects,
                               key=lambda n: (OBJECT_CONFIG.get(n, {}).get("priority", 3),
                                              -current_labels[n][1])):
                dist, area, direction, x1, y1, x2, y2 = current_labels[name]
                msg = build_navigation_message(
                    name, dist, direction, area, latest_frame, x1, y1, x2, y2)

                if msg:
                    to_speak.append(msg)
                    spoken_names.append(name)
                    self._known.add(name)
                    # BUG 2 FIX: do NOT pre-stamp last_spoken here.
                    # Stamp happens in _worker AFTER speech finishes.
                else:
                    # Below threshold — track in pending so we re-check every cooldown
                    # BUG 2 FIX: do NOT add to _known, do NOT stamp last_spoken.
                    # Keep in _pending so next update() re-evaluates threshold.
                    self._pending.add(name)

            # ── Pending objects — re-evaluate threshold every frame ────────────
            # These were seen before but were below their speak_at threshold
            for name in sorted(self._pending,
                               key=lambda n: (OBJECT_CONFIG.get(n, {}).get("priority", 3),
                                              -current_labels.get(n, ("",0,"",0,0,0,0))[1])):
                if name not in current_labels:
                    continue
                dist, area, direction, x1, y1, x2, y2 = current_labels[name]
                msg = build_navigation_message(
                    name, dist, direction, area, latest_frame, x1, y1, x2, y2)
                if msg:
                    # Threshold now met — graduate from pending to known
                    to_speak.append(msg)
                    spoken_names.append(name)
                    self._pending.discard(name)
                    self._known.add(name)

            # ── Known objects past cooldown — re-announce ──────────────────────
            for name in sorted(self._known - set(spoken_names),
                               key=lambda n: (OBJECT_CONFIG.get(n, {}).get("priority", 3),
                                              -current_labels.get(n, ("",0,"",0,0,0,0))[1])):
                if name not in current_labels:
                    continue
                if now - self._last_spoken.get(name, 0) > COOLDOWN:
                    dist, area, direction, x1, y1, x2, y2 = current_labels[name]
                    msg = build_navigation_message(
                        name, dist, direction, area, latest_frame, x1, y1, x2, y2)
                    if msg:
                        to_speak.append(msg)
                        spoken_names.append(name)

        # ── Queue OUTSIDE lock ─────────────────────────────────────────────────
        if not to_speak:
            return

        # BUG 3 FIX: always queue the announcement even if queue has an item.
        # Use maxsize-aware put: if queue already has 1 item pending, replace it
        # with the fresh combined announcement so stale speech never plays.
        announcement = " ".join(to_speak)

        # Drain any pending stale item, then put fresh one
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

        # BUG 4 FIX: store which names this announcement covers for stamping
        with self._lock:
            self._pending_stamp = spoken_names[:]

        self._queue.put(announcement)

    def speak_scene(self, message: str):
        """Queue a scene description only if no object alert is pending.
        Scene messages are ambient context — never interrupt hazard warnings."""
        if self._queue.qsize() == 0:
            with self._lock:
                self._pending_stamp = []
            self._queue.put(message)

    def stop(self):
        self._queue.put(None)


# ── Shared state ───────────────────────────────────────────────────────────────
latest_boxes      = []
latest_frame_copy = None
boxes_lock        = threading.Lock()
speech            = SpeechManager()
scene_engine      = SceneEngine()

# ── Inference thread ───────────────────────────────────────────────────────────
inference_buffer = deque(maxlen=CONFIRM_FRAMES)

def inference_worker():
    global latest_frame_copy
    print("Inference thread started", flush=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=CONF, iou=IOU, imgsz=IMG_SIZE, verbose=False)

        boxes          = []
        current_labels = {}

        for box in results[0].boxes:
            cls  = int(box.cls[0])
            name = model.names[cls]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)

            dist      = ("Very Near" if area > 50000
                         else "Near" if area > 15000
                         else "Far")
            cx        = (x1 + x2) // 2
            direction = get_direction(cx, FRAME_W)

            # Build nav message for display label
            nav_msg = build_navigation_message(
                name, dist, direction, area, frame, x1, y1, x2, y2)
            display_label = nav_msg if nav_msg else f"{name} - {dist} - {direction}"

            boxes.append((name, dist, direction, x1, y1, x2, y2, area, conf, display_label))

            # current_labels stores everything speech manager needs
            if name not in current_labels or area > current_labels[name][1]:
                current_labels[name] = (dist, area, direction, x1, y1, x2, y2)

        with boxes_lock:
            latest_boxes[:]      = boxes
            latest_frame_copy    = frame.copy()

        inference_buffer.append(set(current_labels.keys()))

        if len(inference_buffer) == CONFIRM_FRAMES:
            stable = set.intersection(*inference_buffer)
            speech.update(stable, current_labels, frame)

            # Scene understanding — runs after object alerts, never interrupts them
            if stable:
                # Count instances per class for crowd detection
                obj_counts = {}
                for (n, *_) in boxes:
                    obj_counts[n] = obj_counts.get(n, 0) + 1

                result = scene_engine.infer(stable, obj_counts)
                if result:
                    display_text, scene_msg = result
                    if scene_msg:
                        speech.speak_scene(scene_msg)

        if current_labels:
            det = ", ".join(
                f"{n}({round(next(b[8] for b in boxes if b[0]==n)*100)}%)"
                for n in current_labels
            )
            print(f"[DETECTED] {det}", flush=True)

threading.Thread(target=inference_worker, daemon=True).start()

# ── FPS ────────────────────────────────────────────────────────────────────────
fps_prev = time.time()
fps_cnt  = 0
fps_disp = 0

print("Running — press Q to quit", flush=True)

# ── Priority colour map ────────────────────────────────────────────────────────
def get_color(name: str):
    p = OBJECT_CONFIG.get(name, {}).get("priority", 3)
    return (0,0,255) if p==0 else (0,140,255) if p==1 else (0,220,0)

# ── Display loop ───────────────────────────────────────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera read failed", flush=True)
        break

    with boxes_lock:
        boxes = list(latest_boxes)

    for (name, dist, direction, x1, y1, x2, y2, area, conf, display_label) in boxes:
        color = get_color(name)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Truncate label if too long for the box width
        max_chars  = max(10, (x2 - x1) // 8)
        short_label = (display_label[:max_chars] + "..") if len(display_label) > max_chars else display_label

        cv2.putText(frame, short_label,
                    (x1, max(y1 - 8, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2)

        # Confidence badge bottom-right of box
        cv2.putText(frame, f"{round(conf*100)}%",
                    (x2 - 38, y2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    # ── Zone dividers (visual Left / Center / Right guide) ────────────────
    third = FRAME_W // 3
    cv2.line(frame, (third, 0), (third, FRAME_H), (80, 80, 80), 1)
    cv2.line(frame, (2*third, 0), (2*third, FRAME_H), (80, 80, 80), 1)
    cv2.putText(frame, "LEFT",   (8, FRAME_H-28),         cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80,80,80), 1)
    cv2.putText(frame, "CENTER", (third+4, FRAME_H-28),   cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80,80,80), 1)
    cv2.putText(frame, "RIGHT",  (2*third+4, FRAME_H-28), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (80,80,80), 1)

    fps_cnt += 1
    if time.time() - fps_prev >= 1.0:
        fps_disp = fps_cnt
        fps_cnt  = 0
        fps_prev = time.time()

    cv2.putText(frame, f"FPS:{fps_disp}  VisionGuide AI",
                (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,210,255), 2)
    cv2.putText(frame, "RED=Hazard  ORANGE=Obstacle  GREEN=Object",
                (8, FRAME_H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180,180,180), 1)

    # Scene label — top-right corner, cyan background pill
    scene_label = scene_engine.current_display
    if scene_label:
        (tw, th), _ = cv2.getTextSize(scene_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        rx1 = FRAME_W - tw - 16
        cv2.rectangle(frame, (rx1 - 4, 6), (FRAME_W - 4, th + 14), (180, 130, 0), -1)
        cv2.putText(frame, scene_label, (rx1, th + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imshow("VisionGuide AI", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

print("Shutting down...", flush=True)
speech.stop()
cap.release()
cv2.destroyAllWindows()
print("Done.", flush=True)
