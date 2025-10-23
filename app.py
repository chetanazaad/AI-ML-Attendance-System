from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta 
import os
import random 

# --- Configuration ---
# Uses SQLite database file named 'attendance.db' in the project root
class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'attendance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'a_secure_development_key_change_me' 

# --- Initialization ---
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# --- Database Models (Tables) ---
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    face_id = db.Column(db.String(80), unique=True, nullable=False) 
    name = db.Column(db.String(80), nullable=False)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    face_id = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_face_id = db.Column(db.String(80), nullable=False) # Stores the recognized face_id
    status = db.Column(db.String(10), default='Present')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) 

# --- Helper function for JSON serialization ---
def serialize_person(person):
    """Converts a Student/Teacher object to a dictionary for JSON response."""
    return {
        'id': person.id,
        'face_id': person.face_id,
        'name': person.name
    }

# --- API Routes ---

# 1. Student Management (FULL CRUD)
@app.route('/api/students', methods=['GET', 'POST'])
def handle_students():
    # CREATE (POST)
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'name' not in data or 'face_id' not in data:
            return jsonify({"error": "Missing name or face_id"}), 400
        
        if Student.query.filter_by(face_id=data['face_id']).first():
            return jsonify({"error": f"Student with face_id '{data['face_id']}' already exists."}), 409
        
        new_student = Student(face_id=data['face_id'], name=data['name'])
        db.session.add(new_student)
        db.session.commit()
        return jsonify({"message": f"Student {new_student.name} added successfully!"}), 201

    # READ ALL (GET)
    if request.method == 'GET':
        students = Student.query.all()
        return jsonify([serialize_person(s) for s in students]), 200

# Read One, Update, and Delete Student by ID
@app.route('/api/students/<int:student_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_student_by_id(student_id):
    student = Student.query.get_or_404(student_id)

    # READ ONE (GET)
    if request.method == 'GET':
        return jsonify(serialize_person(student)), 200

    # UPDATE (PUT)
    if request.method == 'PUT':
        data = request.get_json()
        if 'name' in data:
            student.name = data['name']
        if 'face_id' in data:
            # Simple uniqueness check on update
            if Student.query.filter_by(face_id=data['face_id']).first() and student.face_id != data['face_id']:
                 return jsonify({"error": "Face ID already in use by another student."}), 409
            student.face_id = data['face_id']

        db.session.commit()
        return jsonify({"message": f"Student ID {student_id} updated."}), 200

    # DELETE (DELETE)
    if request.method == 'DELETE':
        db.session.delete(student)
        db.session.commit()
        return jsonify({"message": f"Student ID {student_id} deleted successfully."}), 200


# 2. Teacher Management (FULL CRUD)
@app.route('/api/teachers', methods=['GET', 'POST'])
def handle_teachers():
    # CREATE (POST)
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'name' not in data or 'face_id' not in data:
            return jsonify({"error": "Missing name or face_id"}), 400
        
        if Teacher.query.filter_by(face_id=data['face_id']).first():
            return jsonify({"error": f"Teacher with face_id '{data['face_id']}' already exists."}), 409
        
        new_teacher = Teacher(face_id=data['face_id'], name=data['name'])
        db.session.add(new_teacher)
        db.session.commit()
        return jsonify({"message": f"Teacher {new_teacher.name} added successfully!"}), 201

    # READ ALL (GET)
    if request.method == 'GET':
        teachers = Teacher.query.all()
        return jsonify([serialize_person(t) for t in teachers]), 200

# NEW ROUTE: Read One, Update, and Delete Teacher by ID (Completing CRUD)
@app.route('/api/teachers/<int:teacher_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_teacher_by_id(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)

    # READ ONE (GET)
    if request.method == 'GET':
        return jsonify(serialize_person(teacher)), 200

    # UPDATE (PUT)
    if request.method == 'PUT':
        data = request.get_json()
        if 'name' in data:
            teacher.name = data['name']
        if 'face_id' in data:
            # Simple uniqueness check on update
            if Teacher.query.filter_by(face_id=data['face_id']).first() and teacher.face_id != data['face_id']:
                 return jsonify({"error": "Face ID already in use by another teacher."}), 409
            teacher.face_id = data['face_id']

        db.session.commit()
        return jsonify({"message": f"Teacher ID {teacher_id} updated."}), 200

    # DELETE (DELETE)
    if request.method == 'DELETE':
        db.session.delete(teacher)
        db.session.commit()
        return jsonify({"message": f"Teacher ID {teacher_id} deleted successfully."}), 200


# 3. Attendance Marking (CORE INTEGRATION POINT)
@app.route('/api/attendance/mark', methods=['POST'])
def mark_attendance():
    """Receives data from the face recognition script and logs attendance."""
    data = request.get_json()
    person_face_id = data.get('face_id') 

    if not person_face_id:
        return jsonify({"error": "Missing 'face_id' in request data."}), 400

    # Check if the ID exists in the database tables
    is_known = Student.query.filter_by(face_id=person_face_id).first() or \
               Teacher.query.filter_by(face_id=person_face_id).first()

    if is_known:
        # Create a new attendance record
        new_record = Attendance(
            person_face_id=person_face_id,
            status='Present',
            timestamp=datetime.utcnow() 
        )
        db.session.add(new_record)
        db.session.commit()
        return jsonify({"message": f"Attendance marked for {person_face_id}."}), 201
    else:
        return jsonify({"error": f"ID {person_face_id} recognized by AI but not found in DB. Enroll first."}), 404

# 4. Teacher Presence Status (For Vasanthi/Yug Dashboard)
@app.route('/api/teacher/presence', methods=['GET'])
def get_teacher_presence():
    """
    Reports the attendance status of all teachers based on activity in the last 60 minutes.
    This logic is more robust for Vasanthi's absence detection.
    """
    
    teachers = Teacher.query.all()
    teacher_presence = []
    
    # Define the recent activity window (last 60 minutes)
    one_hour_ago = datetime.utcnow() - timedelta(minutes=60)
    
    for teacher in teachers:
        # Check for *any* 'Present' records for this teacher in the last 60 minutes
        is_present = Attendance.query.filter(
            Attendance.person_face_id == teacher.face_id,
            Attendance.status == 'Present',
            Attendance.timestamp >= one_hour_ago # NEW FILTER: Must be present in the last hour
        ).order_by(Attendance.timestamp.desc()).first() is not None
        
        teacher_presence.append({
            'name': teacher.name,
            'face_id': teacher.face_id,
            'status': 'Present' if is_present else 'Absent/Unknown'
        })
        
    return jsonify(teacher_presence), 200
    
# 5. Report Generation API (Chetan's Deliverable)
@app.route('/api/reports/attendance.csv', methods=['GET'])
def generate_attendance_report():
    """Generates and returns attendance data in CSV format."""
    
    records = Attendance.query.order_by(Attendance.timestamp.desc()).all()
    
    # Build the CSV content string
    csv_content = "ID, Status, Timestamp\n"
    for record in records:
        ts_local = record.timestamp.strftime('%Y-%m-%d %H:%M:%S') 
        csv_content += f"{record.person_face_id}, {record.status}, {ts_local}\n"

    # Return the CSV content with the correct MIME type for download
    response = app.response_class(
        response=csv_content,
        status=200,
        mimetype='text/csv'
    )
    response.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    return response

# 6. Quiz Management (For Yug)
@app.route('/api/quiz/data', methods=['GET'])
def get_quiz_data():
    """Provides placeholder MCQ data structure for Yug's frontend."""
    quiz_data = [
        {
            "id": 1,
            "question": "What is the capital of France?",
            "options": ["Berlin", "Madrid", "Paris", "Rome"],
            "answer": "Paris"
        },
        {
            "id": 2,
            "question": "Which module did Chetan use for face recognition?",
            "options": ["PyTorch", "face_recognition", "TensorFlow", "scikit-learn"],
            "answer": "face_recognition"
        }
    ]
    return jsonify(quiz_data), 200

# 7. Chatbot Endpoint (For Nitin and Yug)
@app.route('/api/chatbot', methods=['POST'])
def chatbot_endpoint():
    """Receives user questions and returns a mock response/context."""
    data = request.get_json()
    user_question = data.get('question')
    
    if not user_question:
        return jsonify({"response": "Please provide a question."}), 400

    # In final version, this is where Nitin's LSTM model is called.
    
    context = data.get('context', [])
    
    mock_responses = [
        "The data analysis indicates that solution relies on a well-structured SQLite join.",
        "As an AI, I suggest you consult the API documentation for the correct endpoint.",
        "That question requires integration with the timetable data, which is still pending.",
        f"Regarding '{user_question}', I can provide real-time attendance figures if you ask for them specifically."
    ]
    
    response_text = random.choice(mock_responses)
    
    # Update Context for "memory"
    context.append({"user": user_question})
    context.append({"bot": response_text}) 
    
    return jsonify({
        "response": response_text,
        "context": context[-3:] # Maintain memory of the last 3 exchanges
    }), 200


# --- Run App and Initialize DB ---
with app.app_context():
    db.create_all() # Creates the database file and all defined tables

if __name__ == '__main__':
    app.run(debug=True)
