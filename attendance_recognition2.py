import cv2                        # The go-to library for webcam and image handling
import face_recognition           # Core ML engine for encoding and comparing faces
import os                         # OS utilities for navigating the filesystem
from datetime import datetime     # Gotta time the log entries
import numpy as np                # For fast math (distance calculation)

# --- Configuration: Tweak These ---
KNOWN_FACES_DIR = "training_images"  # Our database location
ATTENDANCE_FILE = "attendance_log.csv" # The log file
TOLERANCE = 0.52                      # How strict the face match needs to be (0.6 is usually fine)

# --- Data Loading (Startup) ---
def load_known_faces():
    """Builds the encoding database from disk on startup."""
    known_face_encodings = []
    known_face_names = []
    
    print("Building face database...")

    # Iterate through all known people's folders
    for name in os.listdir(KNOWN_FACES_DIR):
        if name.startswith('.'):
            continue

        person_dir = os.path.join(KNOWN_FACES_DIR, name)
        for filename in os.listdir(person_dir):
            path = os.path.join(person_dir, filename)
            
            # Load the image and get the 128-D face vector
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            
            if encodings:
                # Store the face's digital 'fingerprint'
                known_face_encodings.append(encodings[0])
                known_face_names.append(name.replace('_', ' ').title())

    print(f"Database built with {len(known_face_encodings)} faces.")
    return known_face_encodings, known_face_names


# --- Attendance Logic ---
def log_attendance(name):
    """Logs the entry, checking if they're already logged in the last hour."""
    
    with open(ATTENDANCE_FILE, 'r+') as f:
        log_data = f.readlines()
        recently_logged = [] 
        
        # Check entries against the 3600-second (1 hour) timeout
        for line in log_data:
            entry = line.split(',')
            try:
                log_time = datetime.strptime(entry[1].strip(), '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - log_time).total_seconds() < 3600:
                    recently_logged.append(entry[0].strip())
            except:
                pass # Skip the header or bad lines

        # Log only if they are not already on the recent list
        if name not in recently_logged:
            now = datetime.now()
            dt_string = now.strftime('%Y-%m-%d %H:%M:%S')
            f.writelines(f'\n{name}, {dt_string}')
            print(f"ATTENDANCE LOGGED: {name} at {dt_string}")
            return True
        return False

# Initialize the CSV log file if it's the first run
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, 'w') as f:
        f.write('Name, Timestamp\n')
    print(f"Created new attendance log: {ATTENDANCE_FILE}")

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
    
    # Gotta convert the color format for the ML model
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Detect faces and generate live encodings
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
            log_attendance(name) # Success! Log it.
            name_label = name
        else:
            # Custom message for unknown faces
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