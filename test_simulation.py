import win32com.client
import pythoncom
import threading
import queue
import time
from collections import deque

COOLDOWN       = 5
CONFIRM_FRAMES = 2

class SpeechManager:
    def __init__(self):
        self._queue       = queue.Queue()
        self._known       = set()
        self._last_spoken = {}
        self._lock        = threading.Lock()
        self._thread      = threading.Thread(target=self._worker, daemon=False)
        self._thread.start()

    def _worker(self):
        pythoncom.CoInitialize()
        sapi = win32com.client.Dispatch('SAPI.SpVoice')
        sapi.Rate = -1
        while True:
            text = self._queue.get()
            if text is None:
                break
            print(f'  >>> SPEAKING: {text}', flush=True)
            sapi.Speak(text)
            print(f'  >>> DONE: {text}', flush=True)
            name = text.split()[0]
            with self._lock:
                self._last_spoken[name] = time.time()
            self._queue.task_done()
        pythoncom.CoUninitialize()

    def update(self, stable_names, current_labels):
        now = time.time()
        to_speak = []

        with self._lock:
            new_objects = stable_names - self._known
            gone = self._known - stable_names
            self._known -= gone

            for name in sorted(new_objects,
                               key=lambda n: current_labels[n][1], reverse=True):
                to_speak.append(f"{name} {current_labels[name][0]}")
                self._known.add(name)
                self._last_spoken[name] = now

            for name in sorted(self._known - new_objects,
                               key=lambda n: current_labels.get(n, ('',0))[1], reverse=True):
                if name not in current_labels:
                    continue
                if now - self._last_spoken.get(name, 0) > COOLDOWN:
                    to_speak.append(f"{name} {current_labels[name][0]}")
                    self._last_spoken[name] = now

        if not to_speak:
            return
        self._queue.put(", ".join(to_speak))

    def stop(self):
        self._queue.put(None)
        self._thread.join()


speech = SpeechManager()
inference_buffer = deque(maxlen=CONFIRM_FRAMES)

def run_frames(label, detections, count=3):
    """Simulate N inference frames with given detections."""
    for _ in range(count):
        inference_buffer.append(set(detections.keys()))
        if len(inference_buffer) == CONFIRM_FRAMES:
            stable = set.intersection(*inference_buffer)
            speech.update(stable, detections)
        time.sleep(0.1)

print("=== FRAME 1-3: Only person ===", flush=True)
run_frames("person only", {"person": ("Very Near", 80000)}, count=4)
time.sleep(3)

print("=== FRAME 4-6: Person + Bottle ===", flush=True)
run_frames("person+bottle", {"person": ("Very Near", 80000), "bottle": ("Far", 8000)}, count=4)
time.sleep(3)

print("=== FRAME 7-9: Person + Bottle + Chair ===", flush=True)
run_frames("p+b+c", {"person": ("Very Near", 80000), "bottle": ("Far", 8000), "chair": ("Near", 20000)}, count=4)
time.sleep(4)

print("=== FRAME 10-12: Same objects (no repeat expected) ===", flush=True)
run_frames("same", {"person": ("Very Near", 80000), "bottle": ("Far", 8000), "chair": ("Near", 20000)}, count=4)
time.sleep(2)

print("=== FRAME 13-15: Chair disappears ===", flush=True)
run_frames("no chair", {"person": ("Very Near", 80000), "bottle": ("Far", 8000)}, count=4)
time.sleep(2)

print("=== FRAME 16-18: Chair reappears (should announce again) ===", flush=True)
run_frames("chair back", {"person": ("Very Near", 80000), "bottle": ("Far", 8000), "chair": ("Near", 20000)}, count=4)
time.sleep(4)

print("=== ALL SIMULATION DONE ===", flush=True)
speech.stop()
