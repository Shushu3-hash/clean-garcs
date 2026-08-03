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


def test_session_start_accepts_string_student_id(client):
    with app.app_context():
        student = Student(name='String Student', grade=6, email='string@example.com', password_hash='x')
        db.session.add(student)
        db.session.commit()
        student_id = str(student.id)

    response = client.post('/api/session/start', json={'student_id': student_id})
    assert response.status_code == 200
    assert response.get_json()['student_id'] == int(student_id)


def test_answer_and_progress_use_student_id_from_request(client):
    with app.app_context():
        student = Student(name='Progress Student', grade=7, email='progress@example.com', password_hash='x')
        db.session.add(student)
        db.session.commit()
        skill_state = StudentSkillState(student_id=student.id, skill_tag='literal', mastery=0.50, points=0)
        db.session.add(skill_state)
        db.session.commit()
        student_id = str(student.id)

    question_response = client.get('/api/question/next', query_string={'student_id': student_id})
    assert question_response.status_code == 200
    payload = question_response.get_json()
    assert 'question_id' in payload

    answer_response = client.post('/api/answer', json={
        'student_id': student_id,
        'question_id': payload['question_id'],
        'chosen_index': 0,
        'response_time_sec': 15,
        'reread_count': 0,
    })
    assert answer_response.status_code == 200
    answer_payload = answer_response.get_json()
    assert answer_payload['points_earned'] >= 0

    progress_response = client.get(f'/api/progress/{student_id}')
    assert progress_response.status_code == 200
    progress_payload = progress_response.get_json()
    assert progress_payload['student_id'] == student.id
    assert progress_payload['badges'] == []
