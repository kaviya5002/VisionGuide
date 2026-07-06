from ultralytics import YOLO
import cv2
import win32com.client
import pythoncom
import threading
import queue
import time
from collections import deque

print("ALL IMPORTS OK", flush=True)

# Test YOLO loads
model = YOLO("yolov8n.pt")
print("YOLO MODEL OK", flush=True)

# Test camera opens
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
print("CAMERA OPENED:", cap.isOpened(), flush=True)
cap.release()

# Test SAPI speech with multiple phrases
print("TESTING SPEECH...", flush=True)
pythoncom.CoInitialize()
sapi = win32com.client.Dispatch('SAPI.SpVoice')
sapi.Rate = -1
sapi.Speak("person very near")
print("PHRASE 1 OK", flush=True)
sapi.Speak("bottle far")
print("PHRASE 2 OK", flush=True)
sapi.Speak("chair near")
print("PHRASE 3 OK", flush=True)
pythoncom.CoUninitialize()

print("ALL SYSTEMS OK - READY TO RUN", flush=True)
