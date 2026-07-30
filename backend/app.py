from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from flask_bcrypt import Bcrypt

import numpy as np
import joblib
import os
import csv

from mastery import SkillState, SKILLS, apply_response
from sequencing import pick_next_question


# =====================================
# APP SETUP
# =====================================
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)


# =====================================
# DATABASE MODELS
# =====================================
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100))
#     grade = db.Column(db.Integer)




# class Attempt(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer)

#     # ML FEATURES
#     lit_acc = db.Column(db.Float)
#     inf_acc = db.Column(db.Float)
#     voc_acc = db.Column(db.Float)
#     mid_acc = db.Column(db.Float)
#     overall = db.Column(db.Float)
#     time_f = db.Column(db.Float)
#     diff = db.Column(db.Integer)

#     # OUTPUTS
#     lexile = db.Column(db.Integer)
#     band = db.Column(db.Integer)

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    grade = db.Column(db.Integer)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))

class Passage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    grade_band = db.Column(db.Integer) # e.g. 5-7 vs 8-10

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passage_id = db.Column(db.Integer, db.ForeignKey('passage.id'))
    prompt = db.Column(db.Text)
    choices = db.Column(db.JSON) # ["A...", "B...", "C...", "D..."]
    correct_index = db.Column(db.Integer)
    skill_tag = db.Column(db.String(20)) # literal | inferential | critical
    difficulty = db.Column(db.String(10)) # easy | medium | hard

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    skill_tag = db.Column(db.String(20))
    difficulty = db.Column(db.String(10))
    is_correct = db.Column(db.Boolean)
    response_time_sec = db.Column(db.Float)
    reread_count = db.Column(db.Integer, default=0)
    mastery_before = db.Column(db.Float)
    mastery_after = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class StudentSkillState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    skill_tag = db.Column(db.String(20))
    mastery = db.Column(db.Float, default=0.50)
    points = db.Column(db.Integer, default=0)


# Compatibility aliases for older route names
User = Student
Attempt = Response


# =====================================
# LOAD ML MODELS
# =====================================
MODEL_RF_PATH = "rf_model.pkl"
MODEL_SVM_PATH = "svm_model.pkl"

rf_model = None
svm_model = None


def load_models():
    global rf_model, svm_model

    if os.path.exists(MODEL_RF_PATH) and os.path.exists(MODEL_SVM_PATH):
        print("✅ Loading ML models...")
        rf_model = joblib.load(MODEL_RF_PATH)
        svm_model = joblib.load(MODEL_SVM_PATH)
    else:
        print("⚠️ Models not found. Run train_model.py first.")


# =====================================
# INIT DB + LOAD MODELS
# =====================================
with app.app_context():
    db.create_all()
    load_models()


# =====================================
# HEALTH CHECK + SERVE FRONTEND
# =====================================
@app.route("/")
def home():
    return send_file('../frontend/dashboard.html')

@app.route("/library")
def library():
    return send_file('../frontend/library.html')

@app.route("/progress")
def progress():
    return send_file('../frontend/progress.html')



def _get_or_create_skill_state(student_id, skill_tag):
    state_row = StudentSkillState.query.filter_by(student_id=student_id, skill_tag=skill_tag).first()
    if state_row is None:
        state_row = StudentSkillState(student_id=student_id, skill_tag=skill_tag, mastery=0.50, points=0)
        db.session.add(state_row)
        db.session.commit()

    return state_row


# =====================================
# REGISTER USER
# =====================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}

    if not data.get("name") or not data.get("grade"):
        return jsonify({"error": "Missing name or grade"}), 400

    student = Student(
        name=data['name'],
        grade=data['grade'],
        email=data.get('email') or f"student{datetime.utcnow().timestamp()}@garcs.local",
        password_hash=""
    )

    db.session.add(student)
    db.session.commit()

    return jsonify({"user_id": student.id, "student_id": student.id})


# =====================================
# GET PASSAGE DIFFICULTY (SIMPLE LOGIC)
# =====================================
@app.route('/api/passage/<int:grade>', methods=['GET'])
def get_passage(grade):

    if grade <= 5:
        difficulty = 0
    elif grade <= 8:
        difficulty = 1
    else:
        difficulty = 2

    return jsonify({
        "difficulty": difficulty
    })


# =====================================
# NEXT QUESTION (MASTERY + SEQUENCING)
# =====================================
@app.route('/api/next-question', methods=['POST'])
@app.route('/api/next_question', methods=['POST'])
def next_question():
    data = request.json or {}
    student_id = data.get('student_id')
    answered_ids = data.get('answered_ids', [])

    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    states = {}
    for skill_tag in SKILLS:
        state_row = _get_or_create_skill_state(student_id, skill_tag)
        states[skill_tag] = SkillState(
            student_id=student_id,
            skill_tag=skill_tag,
            mastery=float(state_row.mastery or 0.50),
            attempts=0,
            correct_count=0,
        )

    def fetch_candidates(skill_tag, difficulty):
        return Question.query.filter_by(skill_tag=skill_tag, difficulty=difficulty).all()

    question, skill_tag, difficulty = pick_next_question(
        states,
        fetch_candidates,
        answered_ids=answered_ids,
        exploration_rate=data.get('exploration_rate', 0.15),
    )

    if question is None:
        return jsonify({
            "question": None,
            "skill_tag": skill_tag,
            "difficulty": difficulty,
            "message": "No matching questions remain"
        })

    return jsonify({
        "question": {
            "id": question.id,
            "prompt": question.prompt,
            "choices": question.choices,
            "skill_tag": question.skill_tag,
            "difficulty": question.difficulty,
        },
        "skill_tag": skill_tag,
        "difficulty": difficulty,
        "mastery": round(states[skill_tag].mastery, 3),
    })


# =====================================
# ML PREDICTION (RF + SVM ENSEMBLE)
# =====================================
@app.route('/api/predict', methods=['POST'])
def predict():
    global rf_model, svm_model

    if rf_model is None or svm_model is None:
        return jsonify({"error": "Models not loaded"}), 500

    data = request.json

    try:
        features = np.array([[
            data['lit_acc'],
            data['inf_acc'],
            data['voc_acc'],
            data['mid_acc'],
            data['overall'],
            data['time_f'],
            data['diff']
        ]])
    except KeyError as e:
        return jsonify({"error": f"Missing field {str(e)}"}), 400

    # Model predictions
    rf_prob = rf_model.predict_proba(features)[0]
    svm_prob = svm_model.predict_proba(features)[0]

    # Ensemble (average)
    combined = (rf_prob + svm_prob) / 2
    band = int(np.argmax(combined))

    # Convert to Lexile
    lexile_base = [300, 500, 700, 860, 1100, 1300]
    offset = int((data['overall'] - 0.5) * 100)
    lexile = max(100, min(1400, lexile_base[band] + offset))

    return jsonify({
        "band": band,
        "lexile": lexile,
        "confidence": float(np.max(combined))
    })


# =====================================
# SAVE ATTEMPT (DATA COLLECTION CORE)
# =====================================
@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.json or {}

    student_id = data.get('student_id') or data.get('user_id')
    question_id = data.get('question_id')
    if not student_id or question_id is None:
        return jsonify({"error": "Missing student_id or question_id"}), 400

    question = Question.query.get(question_id)
    if question is None:
        return jsonify({"error": "Question not found"}), 404

    skill_tag = data.get('skill_tag', question.skill_tag)
    difficulty = data.get('difficulty', question.difficulty)
    is_correct = bool(data.get('is_correct', False))
    response_time_sec = data.get('response_time_sec', 0.0)
    reread_count = data.get('reread_count', 0)

    state_row = _get_or_create_skill_state(student_id, skill_tag)
    state = SkillState(
        student_id=student_id,
        skill_tag=skill_tag,
        mastery=float(state_row.mastery or 0.50),
        attempts=0,
        correct_count=0,
    )

    mastery_before = apply_response(state, is_correct, difficulty)
    state_row.mastery = state.mastery
    state_row.points += int(is_correct)

    response = Response(
        student_id=student_id,
        question_id=question_id,
        skill_tag=skill_tag,
        difficulty=difficulty,
        is_correct=is_correct,
        response_time_sec=response_time_sec,
        reread_count=reread_count,
        mastery_before=mastery_before,
        mastery_after=state.mastery,
    )

    db.session.add(response)
    db.session.commit()

    return jsonify({
        "message": "saved",
        "mastery_before": round(mastery_before, 3),
        "mastery_after": round(state.mastery, 3),
    })


# =====================================
# EXPORT DATASET TO CSV
# =====================================
@app.route('/api/export', methods=['GET'])
def export_csv():
    responses = Response.query.all()

    with open("dataset.csv", "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "student_id","question_id","skill_tag","difficulty",
            "is_correct","response_time_sec","mastery_before","mastery_after"
        ])

        for response in responses:
            writer.writerow([
                response.student_id,
                response.question_id,
                response.skill_tag,
                response.difficulty,
                int(response.is_correct or 0),
                response.response_time_sec,
                response.mastery_before,
                response.mastery_after,
            ])

    return jsonify({
        "message": "dataset.csv generated",
        "rows": len(responses)
    })


# =====================================
# GET USER HISTORY
# =====================================
@app.route('/api/history/<int:user_id>', methods=['GET'])
def history(user_id):
    responses = Response.query.filter_by(student_id=user_id).all()

    return jsonify([
        {
            "question_id": response.question_id,
            "skill_tag": response.skill_tag,
            "is_correct": response.is_correct,
            "date": response.timestamp.strftime("%Y-%m-%d %H:%M")
        } for response in responses
    ])


# =====================================
# RUN APP
# =====================================
if __name__ == "__main__":
    app.run(debug=True)