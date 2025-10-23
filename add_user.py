import requests

API_STUDENTS = "http://127.0.0.1:5000/api/students"
API_TEACHERS = "http://127.0.0.1:5000/api/teachers"

# --- Function to handle POST request and provide clean feedback ---
def add_user(url, name, face_id):
    """Sends a POST request to the specified API endpoint to add a user."""
    payload = {"name": name, "face_id": face_id}
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 201:
            print(f"SUCCESS: {name} ({face_id}) added to DB.")
        elif response.status_code == 409:
            print(f"SKIPPED: {name} ({face_id}) already exists in DB.")
        else:
            # Handle unexpected errors
            error_msg = response.json().get('error', 'Unknown response.')
            print(f"FAILED: {name} - Status {response.status_code}, Error: {error_msg}")

    except requests.exceptions.ConnectionError:
        print(f"FATAL: Cannot connect to Flask server at {url}. Is app.py running?")
        

# --- Add ALL necessary IDs to the database ---
print("\n--- Starting Database Population ---")

# Students (Initial user and Yug's expected ID for testing)
add_user(API_STUDENTS, "Chetan Yadav", "chetan_yadav")
add_user(API_STUDENTS, "Yug Patel", "yug_patel")

# Teachers (Adding the missing IDs that the AI module recognized)
add_user(API_TEACHERS, "Teacher One", "teacher_1")
add_user(API_TEACHERS, "Teacher Two", "teacher_2")

print("--- Data setup complete ---")