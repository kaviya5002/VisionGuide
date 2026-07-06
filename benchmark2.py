from ultralytics import YOLO
import cv2
import time

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Read 5 frames to let camera auto-exposure settle
for _ in range(5):
    ret, frame = cap.read()
cap.release()

print(f"Frame shape: {frame.shape}", flush=True)

model = YOLO('yolov8s.pt')

# Warmup
model(frame, verbose=False)

RUNS = 10
start = time.time()
for _ in range(RUNS):
    results = model(frame, conf=0.25, imgsz=640, verbose=False)
ms = (time.time() - start) / RUNS * 1000

print(f"\nyolov8s conf=0.25 imgsz=640", flush=True)
print(f"  Speed: {ms:.1f} ms/frame  ({1000/ms:.1f} FPS theoretical)", flush=True)
print(f"  Detections: {len(results[0].boxes)}", flush=True)
for box in results[0].boxes:
    name = model.names[int(box.cls[0])]
    conf = round(float(box.conf[0]) * 100, 1)
    x1,y1,x2,y2 = map(int, box.xyxy[0])
    area = (x2-x1)*(y2-y1)
    dist = "Very Near" if area>50000 else "Near" if area>15000 else "Far"
    print(f"    {name:20s} conf={conf}%  dist={dist}", flush=True)
