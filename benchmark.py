from ultralytics import YOLO
import cv2
import time
import numpy as np

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

ret, frame = cap.read()
cap.release()

if not ret:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    print("Using blank frame (camera failed)", flush=True)

RUNS = 5

for model_name in ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt']:
    model = YOLO(model_name)

    # Warmup
    model(frame, verbose=False)

    start = time.time()
    for _ in range(RUNS):
        results = model(frame, conf=0.25, verbose=False)
    elapsed = (time.time() - start) / RUNS * 1000

    detections = results[0].boxes
    det_count = len(detections)
    names = [model.names[int(b.cls[0])] for b in detections]
    confs = [round(float(b.conf[0]) * 100, 1) for b in detections]

    print(f"\n{model_name}", flush=True)
    print(f"  Avg inference : {elapsed:.1f} ms/frame", flush=True)
    print(f"  Detections    : {det_count}", flush=True)
    for n, c in zip(names, confs):
        print(f"    {n}: {c}%", flush=True)
