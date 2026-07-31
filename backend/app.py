from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import csv

# =====================================
# APP SETUP
# =====================================
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)


# =====================================
# DATABASE MODELS  (Chapter 3.6.4 schema — replaces User/Attempt)
# =====================================
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    grade = db.Column(db.Integer)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    # email/password_hash are nullable for now — wired up properly
    # in Phase 3 when /api/login is built. /api/register below only
    # uses name+grade for the moment, same as before.


class Passage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    grade_band = db.Column(db.Integer)  # e.g. 5-7 vs 8-10


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passage_id = db.Column(db.Integer, db.ForeignKey('passage.id'))
    prompt = db.Column(db.Text)
    choices = db.Column(db.JSON)          # ["A...", "B...", "C...", "D..."]
    correct_index = db.Column(db.Integer)
    skill_tag = db.Column(db.String(20))  # literal | inferential | critical
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


# =====================================
# INIT DB
# (no more load_models() call — ML/EdNet strand is fully removed)
# =====================================
with app.app_context():
    db.create_all()


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


# =====================================
# REGISTER STUDENT
# (kept minimal for Phase 1 — same behavior as the old /api/register,
#  just pointed at the new Student model. Login/password comes in Phase 3.)
# =====================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json

    if not data.get("name") or not data.get("grade"):
        return jsonify({"error": "Missing name or grade"}), 400

    student = Student(
        name=data['name'],
        grade=data['grade']
    )

    db.session.add(student)
    db.session.commit()

    # Give the new student a starting mastery row for each of the 3 skills
    # (Chapter 3.6.2 default starting mastery = 0.50, i.e. the column default)
    for skill in ("literal", "inferential", "critical"):
        db.session.add(StudentSkillState(student_id=student.id, skill_tag=skill))
    db.session.commit()

    return jsonify({"student_id": student.id})


# =====================================
# NOTE: everything below this line — /api/passage/<grade>, /api/predict,
# /api/submit, /api/export, /api/history — has been removed on purpose:
#
#   - /api/predict (RF+SVM ensemble) and the ML model loading code are gone.
#     The EdNet/ML strand is fully out of scope now, so there is nothing
#     left to load or call.
#   - /api/passage/<grade>, /api/submit, /api/export, /api/history all
#     referenced the old Attempt schema (lit_acc/inf_acc/voc_acc/mid_acc),
#     which no longer exists. These get rebuilt in Phase 3 against the new
#     schema as /api/question/next, /api/answer, /api/progress/<id>, and a
#     new /api/export — see the roadmap's Phase 3 API table.
#
# Phase 1 is just this file compiling, `db.create_all()` succeeding, and
# /api/register working end-to-end against the new Student model.
# =====================================


# =====================================
# RUN APP
# =====================================
if __name__ == "__main__":
    app.run(debug=True)
