"""
sequencing.py — Adaptive item-selection engine for GARCS.

Given a student's three SkillState objects (literal/inferential/critical),
this module decides which skill + difficulty to serve next, then picks an
unanswered Question row matching that (skill_tag, difficulty).

This is the "adaptive sequencing" half of Chapter 3.6 — mastery.py estimates
*what the student knows*; this module decides *what to show them next*. In
knowledge-tracing terms, mastery.py is the student model, this is the
policy/tutor layer that consumes it (analogous to how a BKT- or PFA-based
ITS uses its mastery estimate to drive item selection, e.g. "mastery
learning" cutoffs in Cognitive Tutor-style systems).
"""

import random
from typing import Iterable, Optional

from mastery import SkillState, target_difficulty, SKILLS


def weakest_skill(states: dict) -> SkillState:
    """
    Pick the skill with the lowest mastery. Ties are broken by fewest
    attempts, so under-practiced skills get explored even if their mastery
    score looks tied with another skill (avoids getting stuck only ever
    testing whichever skill happened to get a low score first).
    """
    return min(states.values(), key=lambda s: (s.mastery, s.attempts))


def choose_next_skill(states: dict, exploration_rate: float = 0.15) -> SkillState:
    """
    Epsilon-greedy wrapper around weakest_skill(): most of the time target
    the weakest skill (exploitation), but occasionally (exploration_rate)
    serve a random *other* skill instead. Pure weakest-skill targeting can
    tunnel-vision on one skill and starve the other two of practice/points,
    which hurts engagement and gives you a thinner evaluation signal for
    Chapter 3.8's mastery-vs-correctness check across all three skills.
    """
    if random.random() < exploration_rate and len(states) > 1:
        return random.choice(list(states.values()))
    return weakest_skill(states)


def pick_next_question(
    states: dict,
    fetch_candidates,
    answered_ids: Iterable[int],
    exploration_rate: float = 0.15,
):
    """
    Parameters
    ----------
    states : dict[str, SkillState]
        The student's current SkillState per skill_tag.
    fetch_candidates : Callable[[str, str], Iterable[QuestionLike]]
        Injected DB lookup: fetch_candidates(skill_tag, difficulty) ->
        questions matching that skill+difficulty. Kept as an injected
        function (not a direct SQLAlchemy query) so this module has zero
        Flask/DB dependencies and can be unit-tested with plain fixtures.
    answered_ids : Iterable[int]
        Question IDs this student has already answered *this session* (or
        ever, depending on how you want repeats to work) — filtered out.
    exploration_rate : float
        See choose_next_skill().

    Returns
    -------
    (question, skill_tag, difficulty) or (None, skill_tag, difficulty) if
    the exact-match pool is exhausted, so the caller can decide a fallback
    (e.g. relax difficulty by one tier, or serve a spaced-repetition item —
    see relax_difficulty() / pick_review_item() below).
    """
    skill_state = choose_next_skill(states, exploration_rate)
    difficulty = target_difficulty(skill_state.mastery)

    answered = set(answered_ids)
    candidates = [q for q in fetch_candidates(skill_state.skill_tag, difficulty) if q.id not in answered]

    if candidates:
        return random.choice(candidates), skill_state.skill_tag, difficulty

    return None, skill_state.skill_tag, difficulty


def relax_difficulty(difficulty: str) -> Optional[str]:
    """
    Fallback when the exact-match question pool for (skill, difficulty) is
    exhausted: step toward "medium" first (the most commonly authored
    tier), since your seed content will likely be uneven across
    skill x difficulty cells early on.
    """
    order = ["easy", "medium", "hard"]
    if difficulty == "medium":
        return None  # nothing left to relax to; caller should try another skill
    idx = order.index(difficulty)
    # step toward the middle
    return order[idx - 1] if idx > 1 else order[idx + 1]


def pick_review_item(fetch_missed, student_id: int, skill_tag: str):
    """
    Optional spaced-repetition hook: re-serve a previously *missed* item for
    this skill after some delay, instead of only ever serving brand-new
    items. This isn't in your current Chapter 3 methodology, but it's a
    low-effort, well-established addition (the spacing effect) worth
    mentioning as a "possible future enhancement" if a panelist asks how
    GARCS handles forgetting — plain rule-based mastery (unlike BKT, which
    has an explicit forget parameter P(F)) doesn't model decay on its own.

    fetch_missed : Callable[[int, str], Iterable[QuestionLike]]
        Injected lookup for previously-answered-incorrectly items for this
        student+skill that haven't been re-served recently.
    """
    candidates = list(fetch_missed(student_id, skill_tag))
    return random.choice(candidates) if candidates else None
