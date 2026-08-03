"""
test_engine.py — Unit tests for mastery.py + sequencing.py.

Run with: pytest backend/test_engine.py -v
(or: python -m pytest backend/test_engine.py -v)

These are pure-Python tests with no Flask/DB dependency, matching Phase 2
of the roadmap ("unit-test the engine before touching Flask routes").
"""

from dataclasses import dataclass

import mastery
import sequencing


# --- mastery.py ---------------------------------------------------------

def test_classify_band_thresholds():
    assert mastery.classify_band(0.10) == mastery.MasteryBand.WEAK
    assert mastery.classify_band(0.39) == mastery.MasteryBand.WEAK
    assert mastery.classify_band(0.40) == mastery.MasteryBand.DEVELOPING
    assert mastery.classify_band(0.69) == mastery.MasteryBand.DEVELOPING
    assert mastery.classify_band(0.70) == mastery.MasteryBand.STRONG
    assert mastery.classify_band(0.95) == mastery.MasteryBand.STRONG


def test_target_difficulty_matches_band():
    assert mastery.target_difficulty(0.20) == "easy"
    assert mastery.target_difficulty(0.55) == "medium"
    assert mastery.target_difficulty(0.85) == "hard"


def test_update_mastery_increases_on_correct():
    m = mastery.update_mastery(0.50, is_correct=True, difficulty="medium")
    assert m > 0.50


def test_update_mastery_decreases_on_incorrect():
    m = mastery.update_mastery(0.50, is_correct=False, difficulty="medium")
    assert m < 0.50


def test_hard_correct_moves_more_than_easy_correct():
    hard_gain = mastery.update_mastery(0.50, True, "hard") - 0.50
    easy_gain = mastery.update_mastery(0.50, True, "easy") - 0.50
    assert hard_gain > easy_gain


def test_easy_incorrect_hurts_more_than_hard_incorrect():
    easy_loss = 0.50 - mastery.update_mastery(0.50, False, "easy")
    hard_loss = 0.50 - mastery.update_mastery(0.50, False, "hard")
    assert easy_loss > hard_loss


def test_mastery_clamped_to_floor_and_ceiling():
    low = 0.10
    for _ in range(50):
        low = mastery.update_mastery(low, is_correct=False, difficulty="easy")
    assert low >= mastery.MASTERY_FLOOR

    high = 0.95
    for _ in range(50):
        high = mastery.update_mastery(high, is_correct=True, difficulty="hard")
    assert high <= mastery.MASTERY_CEILING


def test_apply_response_returns_mastery_before_and_mutates_state():
    state = mastery.SkillState(student_id=1, skill_tag="literal", mastery=0.5)
    before = mastery.apply_response(state, is_correct=True, difficulty="medium")
    assert before == 0.5
    assert state.mastery > 0.5
    assert state.attempts == 1
    assert state.correct_count == 1


# --- sequencing.py --------------------------------------------------------

def make_states(literal=0.5, inferential=0.5, critical=0.5, attempts=(0, 0, 0)):
    return {
        "literal": mastery.SkillState(1, "literal", literal, attempts[0]),
        "inferential": mastery.SkillState(1, "inferential", inferential, attempts[1]),
        "critical": mastery.SkillState(1, "critical", critical, attempts[2]),
    }


def test_weakest_skill_picks_lowest_mastery():
    states = make_states(literal=0.30, inferential=0.60, critical=0.80)
    assert sequencing.weakest_skill(states).skill_tag == "literal"


def test_weakest_skill_tiebreaks_by_fewest_attempts():
    # All three tied at mastery 0.50; critical has the fewest attempts (0),
    # so it should win the tiebreak over literal (10) and inferential (2).
    states = make_states(literal=0.50, inferential=0.50, critical=0.50, attempts=(10, 2, 0))
    assert sequencing.weakest_skill(states).skill_tag == "critical"


def test_choose_next_skill_exploits_when_no_exploration():
    states = make_states(literal=0.20, inferential=0.60, critical=0.80)
    picked = sequencing.choose_next_skill(states, exploration_rate=0.0)
    assert picked.skill_tag == "literal"


@dataclass
class FakeQuestion:
    id: int
    skill_tag: str
    difficulty: str


def test_pick_next_question_filters_answered_and_matches_skill_difficulty():
    states = make_states(literal=0.20, inferential=0.60, critical=0.80)
    pool = [
        FakeQuestion(1, "literal", "easy"),
        FakeQuestion(2, "literal", "easy"),
        FakeQuestion(3, "literal", "medium"),  # wrong difficulty, should be excluded
    ]

    def fetch(skill_tag, difficulty):
        return [q for q in pool if q.skill_tag == skill_tag and q.difficulty == difficulty]

    q, skill_tag, difficulty = sequencing.pick_next_question(
        states, fetch, answered_ids=[1], exploration_rate=0.0
    )
    assert skill_tag == "literal"
    assert difficulty == "easy"
    assert q.id == 2  # id 1 filtered out as already answered


def test_pick_next_question_returns_none_when_pool_exhausted():
    states = make_states(literal=0.20, inferential=0.60, critical=0.80)

    def fetch(skill_tag, difficulty):
        return []

    q, skill_tag, difficulty = sequencing.pick_next_question(
        states, fetch, answered_ids=[], exploration_rate=0.0
    )
    assert q is None
    assert skill_tag == "literal"


def test_relax_difficulty_steps_toward_medium():
    assert sequencing.relax_difficulty("easy") == "medium"
    assert sequencing.relax_difficulty("hard") == "medium"
    assert sequencing.relax_difficulty("medium") is None
