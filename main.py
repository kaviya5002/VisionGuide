import cv2

backends = [
    cv2.CAP_MSMF,     # Microsoft Media Foundation
    cv2.CAP_DSHOW,    # DirectShow
]

for backend in backends:
    print(f"\nTrying backend: {backend}")

    cap = cv2.VideoCapture(0, backend)

    if cap.isOpened():
        print("SUCCESS!")

        while True:
            ret, frame = cap.read()

            if not ret:
                print("Cannot read frame")
                break

            cv2.imshow("Camera Test", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()
        break

    else:
        print("Failed")