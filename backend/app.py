"""
app_phase3.py -- GARCS Phase 3: API layer.

Builds directly on the Phase 1 data model (Student/Passage/Question/Response/
StudentSkillState) and wires it to the Phase 2 rule-based engine
(mastery.py + sequencing.py) via the routes specified in the roadmap's
Phase 3 table:

    /api/register          POST  (extended with password hashing)
    /api/login             POST  (new)
    /api/session/start     POST  (new)
    /api/question/next     GET   (new)
    /api/answer            POST  (new)
    /api/progress/<id>     GET   (new)
    /api/export            GET   (extended for the new Response schema)

/api/predict and /api/passage/<grade> are intentionally NOT present here --
per the roadmap, they're deprecated from the live MVP path.

HOW TO USE THIS FILE
---------------------------------------------------------------------------
1. Put this file, mastery.py, sequencing.py, and seed.py in the same
   backend/ folder, and rename this file to app.py (replacing your Phase 1
   app.py -- the models are identical, this just adds the routes).
2. If you already ran the Phase 1 version and have a database.db with the
   OLD schema (Student without a real password_hash usage, or missing
   rows), delete database.db and re-run seed.py -- SQLite's db.create_all()
   only creates missing tables, it will NOT add new columns to a table
   that already exists on disk.
3. Run `python seed.py` once to populate Passage/Question.
4. Run `python app.py` and hit the endpoints below.

DESIGN DECISIONS WORTH KNOWING ABOUT
---------------------------------------------------------------------------
- Password hashing uses werkzeug.security (generate_password_hash /
  check_password_hash) instead of the roadmap's suggested Flask-Bcrypt.
  Werkzeug ships as a Flask dependency already, so this avoids adding a
  new pip package for a thesis MVP. Swap to Flask-Bcrypt later if you
  want, the call sites are isolated to register()/login().
- No server-side session/cookie state. /api/login verifies credentials
  and returns student_id, but every subsequent call (question/next,
  answer, progress) takes student_id explicitly as a request field/query
  param, matching how /api/register already returns student_id today.
  This sidesteps Flask-CORS + cross-origin cookie configuration
  (supports_credentials=True server-side, credentials:'include' on every
  fetch client-side) which is a common source of silent bugs for a
  frontend/backend served from different ports during local dev. If your
  panel or adviser wants real session-cookie auth, that's a clean Phase 4
  follow-up, not a Phase 3 blocker.
- "Answered questions" = every Question this student has ever answered
  (queried from Response), not scoped to a single login session, since
  Chapter 3.6.4's schema has no Session/attempt-session table. This means
  a student won't be re-served the same question across days, which is
  the more defensible behavior for a mastery-tracking system anyway.
- Points are awarded here (fixed +10 per correct answer, +25 bonus for
  moving up a mastery band) because the roadmap's Phase 3 table itself
  says /api/answer should "award points/badges." Full badge RULES (e.g.
  "3 correct in a row") are still Phase 5 -- /api/progress/<id> already
  returns a `badges` field, just empty for now, so Phase 5 only needs to
  populate it, not change the response shape.
"""

import csv
import io
import random
from datetime import datetime

from flask import Flask, request, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from mastery import (
    SkillState,
    SKILLS,
    classify_band,
    target_difficulty,
    update_mastery,
)
from sequencing import pick_next_question, relax_difficulty

# =====================================
# APP SETUP
# =====================================
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path="",
    instance_path=str(BASE_DIR / "instance"),
    instance_relative_config=True,
)
DATABASE_FILE = Path(app.instance_path) / "database.db"
DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_FILE}"

db = SQLAlchemy(app)
from pathlib import Path

print("=" * 60)
print("INSTANCE:", app.instance_path)
print("DATABASE:", Path(app.instance_path) / "database.db")
print("=" * 60)

CORS(app)


# =====================================
# DATABASE MODELS  (Chapter 3.6.4 schema — unchanged from Phase 1)
# =====================================
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
    grade_band = db.Column(db.Integer)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passage_id = db.Column(db.Integer, db.ForeignKey('passage.id'))
    prompt = db.Column(db.Text)
    choices = db.Column(db.JSON)
    correct_index = db.Column(db.Integer)
    skill_tag = db.Column(db.String(20))
    difficulty = db.Column(db.String(10))


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


with app.app_context():
    db.create_all()


# =====================================
# GAMIFICATION CONSTANTS (Phase 5 will expand on this, not replace it)
# =====================================
POINTS_CORRECT = 10
POINTS_BAND_UP = 25
BAND_RANK = {"Weak": 0, "Developing": 1, "Strong": 2}


# =====================================
# SERVE FRONTEND
# =====================================
@app.route("/")
def home():
    return send_file('../frontend/login.html')


@app.route("/login")
def login_page():
    return send_file('../frontend/login.html')


@app.route("/dashboard")
def dashboard_page():
    return send_file('../frontend/dashboard.html')


@app.route("/library")
def library():
    return send_file('../frontend/library.html')


@app.route("/progress")
def progress_page():
    return send_file('../frontend/progress.html')


# =====================================
# AUTH
# =====================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}

    required = ("name", "grade", "email", "password")
    if not all(data.get(f) for f in required):
        return jsonify({"error": f"Missing one of: {', '.join(required)}"}), 400

    if Student.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "email already registered"}), 409

    student = Student(
        name=data['name'],
        grade=data['grade'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
    )
    db.session.add(student)
    db.session.commit()

    for skill in SKILLS:
        db.session.add(StudentSkillState(student_id=student.id, skill_tag=skill))
    db.session.commit()

    return jsonify({"student_id": student.id})


# @app.route('/api/login', methods=['POST'])
# def login():
#     data = request.json or {}
#     email = data.get("email") or data.get("identifier")
#     password = data.get("password", "")

#     student = Student.query.filter_by(email=email).first()
#     if not student or not student.password_hash or not check_password_hash(student.password_hash, password):
#         return jsonify({"error": "invalid credentials"}), 401

#     return jsonify({"student_id": student.id, "name": student.name, "grade": student.grade})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}

    email = data.get("email") or data.get("identifier")
    password = data.get("password", "")

    student = Student.query.filter_by(email=email).first()

    if not student:
        return jsonify({"error": "student_not_found"}), 404

    if (
        not student.password_hash
        or not check_password_hash(student.password_hash, password)
    ):
        return jsonify({"error": "invalid credentials"}), 401

    return jsonify({
        "student_id": student.id,
        "name": student.name,
        "grade": student.grade
    })

# =====================================
# SESSION START -- ensures skill states exist (idempotent, safe to call every login)
# =====================================
@app.route('/api/session/start', methods=['POST'])
def session_start():
    data = request.json or {}
    student_id = data.get("student_id")

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "student not found"}), 404

    existing = {s.skill_tag for s in StudentSkillState.query.filter_by(student_id=student_id).all()}
    for skill in SKILLS:
        if skill not in existing:
            db.session.add(StudentSkillState(student_id=student_id, skill_tag=skill))
    db.session.commit()

    return jsonify({"student_id": int(student_id), "ready": True})


# =====================================
# ENGINE HELPERS -- bridge DB rows <-> mastery.py's plain SkillState dataclass
# =====================================
def _load_states(student_id):
    """Build {skill_tag: SkillState} from DB rows for sequencing.py to consume."""
    states = {}
    for row in StudentSkillState.query.filter_by(student_id=student_id).all():
        attempts = Response.query.filter_by(student_id=student_id, skill_tag=row.skill_tag).count()
        correct = Response.query.filter_by(student_id=student_id, skill_tag=row.skill_tag, is_correct=True).count()
        states[row.skill_tag] = SkillState(
            student_id=student_id,
            skill_tag=row.skill_tag,
            mastery=row.mastery,
            attempts=attempts,
            correct_count=correct,
        )
    return states


def _fetch_candidates(skill_tag, difficulty):
    return Question.query.filter_by(skill_tag=skill_tag, difficulty=difficulty).all()


@app.route('/api/assessment/passages')
def assessment_passages():
    passages = []
    for passage in Passage.query.order_by(Passage.id).all():
        questions = []
        for question in Question.query.filter_by(passage_id=passage.id).order_by(Question.id).all():
            questions.append({
                "id": question.id,
                "type": {
                    "literal": "literal",
                    "inferential": "inferential",
                    "critical": "main_idea",
                }.get(question.skill_tag, question.skill_tag),
                "q": question.prompt,
                "choices": question.choices or [],
                "correct": question.correct_index,
                "skill_tag": question.skill_tag,
                "difficulty": question.difficulty,
            })

        grade_band = passage.grade_band or 1
        grades = {1: [3, 4, 5], 2: [6, 7, 8], 3: [9, 10, 11, 12]}.get(grade_band, [grade_band * 3])
        difficulty = {1: 0, 2: 1, 3: 2}.get(grade_band, 1)
        word_count = len((passage.body or "").split())
        read_minutes = f"{max(1, word_count // 120)}-{max(2, word_count // 120 + 1)}"

        passages.append({
            "id": passage.id,
            "title": passage.title,
            "genre": "Reading",
            "genreEmoji": "📖",
            "wordCount": max(word_count, 120),
            "readMinutes": read_minutes,
            "grades": grades,
            "difficulty": difficulty,
            "text": passage.body or "",
            "questions": questions,
        })

    return jsonify(passages)


# =====================================
# ADAPTIVE QUESTION SELECTION
# =====================================
@app.route('/api/question/next')
def question_next():
    student_id = request.args.get("student_id", type=int)
    if not student_id or not Student.query.get(student_id):
        return jsonify({"error": "valid student_id required"}), 400

    states = _load_states(student_id)
    if not states:
        return jsonify({"error": "skill states not initialized — call /api/session/start first"}), 400

    answered_ids = [r.question_id for r in Response.query.filter_by(student_id=student_id).all()]

    question, skill_tag, difficulty = pick_next_question(states, _fetch_candidates, answered_ids)

    print("Questions in DB:", Question.query.count())

    print("literal-medium:",
        len(_fetch_candidates("literal", "medium")))

    print("literal-easy:",
        len(_fetch_candidates("literal", "easy")))

    print("inferential-medium:",
        len(_fetch_candidates("inferential", "medium")))

    print("critical-medium:",
        len(_fetch_candidates("critical", "medium")))

    print("States:")
    for s in states.values():
        print(s.skill_tag, s.mastery)

    print("Answered:", answered_ids)

    print("Chosen skill:", skill_tag)
    print("Chosen difficulty:", difficulty)
    print("Question:", question)

    # Fallback chain if the exact (skill, difficulty) pool is empty: relax
    # difficulty toward "medium" first, then fall back to any unanswered
    # question at all. This matters once real usage outpaces a small seed
    # bank, and gives you a concrete answer if a panelist asks "what
    # happens when the question pool runs dry."
    if question is None:
        tried = {difficulty}
        relaxed = relax_difficulty(difficulty)
        while question is None and relaxed and relaxed not in tried:
            tried.add(relaxed)
            candidates = [q for q in _fetch_candidates(skill_tag, relaxed) if q.id not in set(answered_ids)]
            if candidates:
                question = random.choice(candidates)
                difficulty = relaxed
            else:
                relaxed = relax_difficulty(relaxed)

    if question is None:
        remaining = Question.query.filter(~Question.id.in_(answered_ids or [-1])).all()
        if remaining:
            question = random.choice(remaining)
            skill_tag, difficulty = question.skill_tag, question.difficulty

    if question is None:
        return jsonify({"done": True, "message": "No unanswered questions remain in the bank."})

    passage = Passage.query.get(question.passage_id)

    return jsonify({
        "question_id": question.id,
        "prompt": question.prompt,
        "choices": question.choices,
        "skill_tag": skill_tag,
        "difficulty": difficulty,
        "passage": {
            "id": passage.id,
            "title": passage.title,
            "body": passage.body,
        } if passage else None,
    })


# =====================================
# ANSWER SUBMISSION -- logs Response, updates mastery, awards points
# =====================================
@app.route('/api/answer', methods=['POST'])
def answer():
    data = request.json or {}
    student_id = data.get("student_id")
    question_id = data.get("question_id")
    chosen_index = data.get("chosen_index")
    response_time_sec = data.get("response_time_sec", 0.0)
    reread_count = data.get("reread_count", 0)

    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "question not found"}), 404

    skill_row = StudentSkillState.query.filter_by(student_id=student_id, skill_tag=question.skill_tag).first()
    if not skill_row:
        return jsonify({"error": "skill state not initialized — call /api/session/start first"}), 400

    is_correct = (chosen_index == question.correct_index)

    mastery_before = skill_row.mastery
    mastery_after = update_mastery(mastery_before, is_correct, question.difficulty)
    band_before = classify_band(mastery_before)
    band_after = classify_band(mastery_after)

    points_earned = POINTS_CORRECT if is_correct else 0
    leveled_up = BAND_RANK[band_after.value] > BAND_RANK[band_before.value]
    if leveled_up:
        points_earned += POINTS_BAND_UP

    skill_row.mastery = mastery_after
    skill_row.points = (skill_row.points or 0) + points_earned

    db.session.add(Response(
        student_id=student_id,
        question_id=question_id,
        skill_tag=question.skill_tag,
        difficulty=question.difficulty,
        is_correct=is_correct,
        response_time_sec=response_time_sec,
        reread_count=reread_count,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
    ))
    db.session.commit()

    return jsonify({
        "is_correct": is_correct,
        "correct_index": question.correct_index,
        "mastery_before": round(mastery_before, 3),
        "mastery_after": round(mastery_after, 3),
        "band_before": band_before.value,
        "band_after": band_after.value,
        "leveled_up": leveled_up,
        "points_earned": points_earned,
    })


# =====================================
# PROGRESS / DASHBOARD DATA
# =====================================
@app.route('/api/progress/<int:student_id>')
def progress_api(student_id):
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "student not found"}), 404

    rows = StudentSkillState.query.filter_by(student_id=student_id).all()
    skills = []
    total_points = 0
    for row in rows:
        band = classify_band(row.mastery)
        skills.append({
            "skill_tag": row.skill_tag,
            "mastery": round(row.mastery, 3),
            "band": band.value,
            "next_difficulty": target_difficulty(row.mastery),
            "points": row.points,
        })
        total_points += row.points or 0

    return jsonify({
        "student_id": student_id,
        "name": student.name,
        "grade": student.grade,
        "skills": skills,
        "total_points": total_points,
        "badges": [],  # Phase 5 populates this from a real badge-rule table
    })


# =====================================
# EXPORT (Chapter 3.8 evaluation data)
# =====================================
@app.route('/api/export')
def export():
    rows = Response.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "student_id", "passage_id", "question_id", "skill_tag", "difficulty",
        "is_correct", "response_time_sec", "reread_count",
        "mastery_before", "mastery_after", "timestamp",
    ])
    for r in rows:
        q = Question.query.get(r.question_id)
        writer.writerow([
            r.student_id,
            q.passage_id if q else "",
            r.question_id,
            r.skill_tag,
            r.difficulty,
            r.is_correct,
            r.response_time_sec,
            r.reread_count,
            r.mastery_before,
            r.mastery_after,
            r.timestamp,
        ])

    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=garcs_responses.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


# NOTE: /api/predict and /api/passage/<grade> are intentionally absent.
# Per the roadmap, they're deprecated from the live MVP path -- the
# EdNet/ML strand is fully out of scope, so there is nothing left to serve
# from those routes.


if __name__ == "__main__":
    app.run(debug=True)
