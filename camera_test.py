import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

print("Opened:", cap.isOpened())

while True:
    ret, frame = cap.read()

    if not ret:
        print("Failed to read frame")
        break

    cv2.imshow("Live Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()