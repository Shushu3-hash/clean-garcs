import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seed
from app import app, db, Student, StudentSkillState


@pytest.fixture
def client():
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///test_app.db')
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed.seed()

    with app.test_client() as client:
        yield client

    with app.app_context():
        db.drop_all()

    if os.path.exists('test_app.db'):
        os.remove('test_app.db')


def test_session_start_and_question_next_return_content(client):
    with app.app_context():
        student = Student(name='Test Student', grade=5, email='student@example.com', password_hash='x')
        db.session.add(student)
        db.session.commit()
        for skill in ['literal', 'inferential', 'critical']:
            db.session.add(StudentSkillState(student_id=student.id, skill_tag=skill))
        db.session.commit()
        student_id = student.id

    session_resp = client.post('/api/session/start', json={'student_id': student_id})
    assert session_resp.status_code == 200

    question_resp = client.get('/api/question/next', query_string={'student_id': student_id})
    assert question_resp.status_code == 200

    payload = question_resp.get_json()
    assert 'question_id' in payload
    assert payload['prompt']
    assert payload['passage']
