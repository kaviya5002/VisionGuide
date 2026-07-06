from ultralytics import YOLO
import cv2
import pyttsx3
import time

# Load YOLO model
model = YOLO("yolov8m.pt")

# Voice engine
engine = pyttsx3.init()

# Camera
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

last_spoken = ""
last_time = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    results = model(frame, conf=0.45)

    annotated_frame = results[0].plot()

    detected_objects = []

    for box in results[0].boxes:
        cls = int(box.cls[0])
        name = model.names[cls]
        detected_objects.append(name)

    unique_objects = list(set(detected_objects))
    print("Detected:", unique_objects)

    if time.time() - last_time > 5 and unique_objects:
        for obj in unique_objects:
            engine.say(obj)
        engine.runAndWait()
        last_time = time.time()

    cv2.imshow("VisionGuide", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()