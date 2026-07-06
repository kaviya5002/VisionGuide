from ultralytics import YOLO
import cv2
import time

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Let camera settle for 10 frames
for _ in range(10):
    ret, frame = cap.read()
cap.release()

print(f"Frame shape: {frame.shape}", flush=True)

configs = [
    ("yolov8s.pt", 0.30, 640),
    ("yolov8s.pt", 0.30, 1280),
    ("yolov8m.pt", 0.30, 640),
    ("yolov8m.pt", 0.30, 1280),
    ("yolov8x.pt", 0.30, 640),
    ("yolov8x.pt", 0.30, 1280),
]

for model_path, conf, imgsz in configs:
    model = YOLO(model_path)
    model(frame, verbose=False)  # warmup

    RUNS = 3
    start = time.time()
    for _ in range(RUNS):
        results = model(frame, conf=conf, imgsz=imgsz, verbose=False)
    ms = (time.time() - start) / RUNS * 1000

    boxes = results[0].boxes
    print(f"\n{model_path} conf={conf} imgsz={imgsz}", flush=True)
    print(f"  {ms:.0f}ms/frame  {len(boxes)} detections", flush=True)
    for b in sorted(boxes, key=lambda x: float(x.conf[0]), reverse=True):
        name = model.names[int(b.cls[0])]
        c    = round(float(b.conf[0]) * 100, 1)
        print(f"    {name:25s} {c}%", flush=True)
