"""
mastery.py — Rule-based, PFA-inspired student mastery model for GARCS.

Knowledge-tracing lineage
-------------------------
This module is a simplified, interpretable cousin of Performance Factors
Analysis (PFA) (Pavlik, Cen & Koedinger, 2009). Classic PFA fits a logistic
regression per skill j from LOGGED data:

    m(i, j) = beta_j + gamma_j * s_i,j + rho_j * f_i,j
    p(correct) = 1 / (1 + e^-m)

where s_i,j / f_i,j are a student's running counts of prior successes/
failures on skill j, beta_j is the skill's baseline easiness, and gamma_j /
rho_j are learned weights for how much a success/failure moves the needle.

GARCS's MVP has no logged data yet to fit beta/gamma/rho, so this module
replaces the *fitted* logistic weights with *fixed, hand-set* step sizes
(BASE_STEP, DIFF_WEIGHT) and represents the running estimate directly as a
mastery probability in [0, 1] rather than a logit. It keeps PFA's two core
ideas — (1) mastery is a per-skill running estimate, (2) it moves up on
success and down on failure, scaled by item difficulty — while dropping the
statistical fitting step. See the "Upgrade path" note at the bottom for how
to swap in a real fitted PFA model once you have pilot response logs.
"""

from dataclasses import dataclass
from enum import Enum

# --- Config -----------------------------------------------------------------

SKILLS = ("literal", "inferential", "critical")

MASTERY_FLOOR = 0.10
MASTERY_CEILING = 0.95
DEFAULT_STARTING_MASTERY = 0.50  # neutral prior, akin to PFA's beta_j = 0

BASE_STEP = 0.05  # magnitude of one mastery update at "medium" difficulty

# Harder items should move mastery more on success (bigger signal of skill)
# and less on failure (missing a hard item is less damning than missing an
# easy one) — this is the same intuition PFA captures by fitting separate
# gamma_j (success weight) and rho_j (failure weight) per skill, just fixed
# here instead of learned.
DIFF_WEIGHT_CORRECT = {"easy": 0.7, "medium": 1.0, "hard": 1.4}
DIFF_WEIGHT_INCORRECT = {"easy": 1.3, "medium": 1.0, "hard": 0.7}


class MasteryBand(str, Enum):
    WEAK = "Weak"
    DEVELOPING = "Developing"
    STRONG = "Strong"


# Must match Chapter 3.6.2 thresholds exactly.
BAND_THRESHOLDS = {
    MasteryBand.WEAK: (0.0, 0.40),
    MasteryBand.DEVELOPING: (0.40, 0.70),
    MasteryBand.STRONG: (0.70, 1.01),  # upper bound exclusive-safe
}

BAND_TO_DIFFICULTY = {
    MasteryBand.WEAK: "easy",
    MasteryBand.DEVELOPING: "medium",
    MasteryBand.STRONG: "hard",
}


@dataclass
class SkillState:
    student_id: int
    skill_tag: str
    mastery: float = DEFAULT_STARTING_MASTERY
    attempts: int = 0
    correct_count: int = 0

    def band(self) -> MasteryBand:
        return classify_band(self.mastery)


def classify_band(mastery: float) -> MasteryBand:
    """Map a mastery score to Weak/Developing/Strong per Chapter 3.6.2."""
    for band, (low, high) in BAND_THRESHOLDS.items():
        if low <= mastery < high:
            return band
    return MasteryBand.STRONG


def target_difficulty(mastery: float) -> str:
    """Band -> next difficulty to serve (easy/medium/hard)."""
    return BAND_TO_DIFFICULTY[classify_band(mastery)]


def update_mastery(mastery: float, is_correct: bool, difficulty: str) -> float:
    """
    One PFA-style additive update.

    mastery_after = clamp(mastery_before + step)
    step = +BASE_STEP * DIFF_WEIGHT_CORRECT[difficulty]   if correct
           -BASE_STEP * DIFF_WEIGHT_INCORRECT[difficulty] if incorrect
    """
    if difficulty not in ("easy", "medium", "hard"):
        raise ValueError(f"Unknown difficulty: {difficulty}")

    if is_correct:
        step = BASE_STEP * DIFF_WEIGHT_CORRECT[difficulty]
        new_mastery = mastery + step
    else:
        step = BASE_STEP * DIFF_WEIGHT_INCORRECT[difficulty]
        new_mastery = mastery - step

    return max(MASTERY_FLOOR, min(MASTERY_CEILING, new_mastery))


def apply_response(state: SkillState, is_correct: bool, difficulty: str) -> float:
    """
    Mutates `state` in place, returns mastery_before (caller logs
    mastery_before/mastery_after into the Response table per 3.6.4).
    """
    mastery_before = state.mastery
    state.mastery = update_mastery(state.mastery, is_correct, difficulty)
    state.attempts += 1
    state.correct_count += int(is_correct)
    return mastery_before


# --- Upgrade path: swap in a fitted PFA model later -------------------------
#
# Once you have pilot Response logs (student_id, skill_tag, is_correct,
# difficulty, timestamp), you can fit real PFA parameters per skill with:
#
#   from sklearn.linear_model import LogisticRegression
#   # features per (student, skill, attempt-so-far): [prior_successes, prior_failures]
#   # target: is_correct
#   model = LogisticRegression().fit(X, y)   # learns gamma_j, rho_j; intercept ~ beta_j
#
# Then replace update_mastery's fixed step with:
#   m = beta_j + gamma_j * successes_so_far + rho_j * failures_so_far
#   mastery = 1 / (1 + exp(-m))
#
# This turns the "PFA-inspired" label in Chapter 3 into an actual fitted PFA
# model — worth flagging as a "Recommendations for future work" item in
# Chapter 5 if you don't have enough pilot data to fit it reliably within
# your thesis timeline (PFA needs a reasonable number of responses per skill
# per student to fit gamma/rho without overfitting).
