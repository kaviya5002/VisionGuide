from ultralytics import YOLO

for model_name in ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt']:
    model = YOLO(model_name)
    print(f"\n=== {model_name} — {len(model.names)} classes ===", flush=True)
    for k, v in model.names.items():
        print(f"  {k:3d}: {v}", flush=True)
