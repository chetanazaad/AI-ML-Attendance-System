import cv2
import face_recognition
import os
import numpy as np
import requests # Used to send data to the Flask API

# --- Configuration: Tweak These ---
KNOWN_FACES_DIR = "training_images" 
TOLERANCE = 0.52                    # Strictness setting for match
API_ENDPOINT = "http://127.0.0.1:5000/api/attendance/mark" # URL of the Flask endpoint

# --- API Interaction Function ---
# This replaces the old log_attendance (CSV) function
def mark_attendance_via_api(face_id_name):
    """Sends the recognized face ID to the running Flask backend."""
    
    # Payload must match what Flask expects: a JSON with 'face_id'
    payload = {
        "face_id": face_id_name.lower().replace(' ', '_') 
    }

    try:
        # Send the POST request to the Flask server
        response = requests.post(API_ENDPOINT, json=payload)
        
        if response.status_code == 201:
            print(f"[API SUCCESS] Attendance marked for {face_id_name}.")
        else:
            # Handle non-201 responses (like 404 Not Found or potential 409 Conflict if implemented later)
            error_msg = response.json().get('error', 'Unknown server issue.')
            print(f"[API FAIL] Status {response.status_code}: {error_msg}")

    except requests.exceptions.ConnectionError:
        print("[API FATAL] Could not connect to Flask server. Is app.py running?")
    except Exception as e:
        print(f"[API ERROR] An unexpected error occurred: {e}")


# --- Data Loading (Startup) ---
def load_known_faces():
    """Builds the encoding database from disk on startup."""
    known_face_encodings = []
    known_face_names = []
    
    print("Building face database...")

    for name in os.listdir(KNOWN_FACES_DIR):
        if name.startswith('.'):
            continue

        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        for filename in os.listdir(person_dir):
            path = os.path.join(person_dir, filename)
            
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_names.append(name.replace('_', ' ').title())

    print(f"Database built with {len(known_face_encodings)} faces.")
    return known_face_encodings, known_face_names

# --- Main Video Loop ---

known_face_encodings, known_face_names = load_known_faces()

cap = cv2.VideoCapture(0) # Open the default webcam. Change '0' if it fails.

if not cap.isOpened():
    print("Fatal Error: Couldn't open the webcam.")
    exit()

print("\nStarting stream. Press 'q' to kill the process.")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    # Process the frame at 1/4 size for major speed boost
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    
    # Color space conversion: OpenCV (BGR) -> face_recognition (RGB)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    name_label = "Scanning..." 

    for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
        
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, TOLERANCE)
        
        # Find the single closest match by calculating the distance
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        
        # Final decision: if best match is within our strictness tolerance
        if matches[best_match_index] and face_distances[best_match_index] < TOLERANCE:
            name = known_face_names[best_match_index]
            
            # --- CORE INTEGRATION POINT ---
            mark_attendance_via_api(name) # Success! Send to Flask API/DB
            
            name_label = name
        else:
            # Display custom message for unknown users
            name_label = "Face not match - UPDATE DATABASE" 

        # Scale coordinates back up to the original frame size
        top *= 4; right *= 4; bottom *= 4; left *= 4

        # Set color: Green for Known, Red for Unknown
        color = (0, 255, 0) if name_label not in ("Face not match - UPDATE DATABASE", "Scanning...") else (0, 0, 255)
        
        # Draw the box and text
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name_label, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)

    # Show the video feed
    cv2.imshow('AI/ML Face Recognition Attendance', frame)

    # Kill the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup time!
cap.release()
cv2.destroyAllWindows()
print("Attendance system terminated.")
