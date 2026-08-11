from ultralytics import YOLO
import cv2

# Load the pretrained YOLOv8 model
model = YOLO("yolov8s.pt")  # small model for speed

# Open webcam (0 = default)
cap = cv2.VideoCapture(0)

# To store previous set of detected class names
previous_classes = set()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Run inference
    results = model(frame, verbose=False)

    # Extract current detected class names
    current_classes = set()
    for r in results:
        if r.boxes is not None:
            cls_ids = r.boxes.cls.tolist()
            class_names = [model.names[int(cls_id)] for cls_id in cls_ids]
            current_classes.update(class_names)

    # Compare with previous classes
    if current_classes != previous_classes:
        print(f"New objects detected: {current_classes - previous_classes}")
        previous_classes = current_classes

        # Show frame only when new objects are detected
        annotated_frame = results[0].plot()
        cv2.imshow("New Detection", annotated_frame)

    # Allow pressing 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
