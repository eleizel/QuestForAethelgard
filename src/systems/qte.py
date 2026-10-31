"""Quick Time Event (QTE) system for Elite and Boss encounters."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from src.config import SND_CRIT, SND_HIT
from src.core.audio import audio

if TYPE_CHECKING:
    from src.systems.combat import CombatSystem

# Screen placement & geometry constants (256x256 display)
QTE_MIN_BUTTONS: Final[int] = 3
QTE_MAX_BUTTONS: Final[int] = 5
QTE_X_MIN: Final[int] = 44
QTE_X_MAX: Final[int] = 212
QTE_Y_MIN: Final[int] = 62
QTE_Y_MAX: Final[int] = 174
QTE_BUTTON_RADIUS: Final[int] = 10
QTE_START_RADIUS: Final[float] = 32.0

# Timing constants (at 30 FPS, 22px span at 0.75..1.25 px/frame -> ~0.59s..0.98s per button)
QTE_MIN_SHRINK_SPEED: Final[float] = 0.75
QTE_MAX_SHRINK_SPEED: Final[float] = 1.25
QTE_OVERSHOOT_GRACE: Final[float] = 1.2
QTE_INTRO_FRAMES: Final[int] = 75
QTE_FEEDBACK_FRAMES: Final[int] = 20
QTE_SUMMARY_FRAMES: Final[int] = 45


def _t(key: str, **kwargs) -> str:
    from src.core.i18n import t
    return t(key, **kwargs)


def classify_qte_tier(score: int) -> str:
    """Classify a 0..100 QTE accuracy score into one of the five resolution tiers."""
    if score <= 20:
        return "failed"
    if score <= 40:
        return "good"
    if score <= 60:
        return "nice"
    if score <= 80:
        return "amazing"
    return "perfect"


@dataclass
class QTETarget:
    """One shrinking-circle QTE button inside a multi-button QTE sequence."""

    x: int
    y: int
    number: int
    button_radius: int = QTE_BUTTON_RADIUS
    start_radius: float = QTE_START_RADIUS
    current_radius: float = QTE_START_RADIUS
    shrink_speed: float = 0.95
    resolved: bool = False
    score: int = 0
    tier: str = ""
    feedback_frames: int = 0

    def current_accuracy(self) -> int:
        """Return 0% at start_radius and 100% when current_radius meets button_radius."""
        span = self.start_radius - self.button_radius
        if span <= 0:
            return 100
        if self.current_radius >= self.start_radius:
            return 0
        if self.current_radius <= self.button_radius:
            return 100
        pct = 100.0 * (self.start_radius - self.current_radius) / span
        return max(0, min(100, int(round(pct))))

    def step_shrink(self) -> bool:
        """Shrink the approach ring by one frame and return True if it missed past the button edge."""
        self.current_radius -= self.shrink_speed
        return self.current_radius < self.button_radius - QTE_OVERSHOOT_GRACE


@dataclass
class QTESequence:
    """Tracks a sequence of 3 to 5 consecutive QTE buttons and their final average resolution."""

    targets: list[QTETarget]
    current_index: int = 0
    intro_frames: int = QTE_INTRO_FRAMES
    summary_active: bool = False
    summary_frames: int = 0
    final_score: int = 0
    final_tier: str = ""
    bonuses_applied: list[str] = field(default_factory=list)

    @property
    def in_intro(self) -> bool:
        return self.intro_frames > 0 and not self.summary_active

    @property
    def current_target(self) -> QTETarget | None:
        if 0 <= self.current_index < len(self.targets):
            return self.targets[self.current_index]
        return None


def generate_qte_sequence(rng: random.Random, count: int | None = None) -> QTESequence:
    """Create a new QTESequence of 3 to 5 randomized target buttons."""
    num_targets = count if count is not None else rng.randint(QTE_MIN_BUTTONS, QTE_MAX_BUTTONS)
    targets: list[QTETarget] = []
    for _ in range(num_targets):
        x = rng.randint(QTE_X_MIN, QTE_X_MAX)
        y = rng.randint(QTE_Y_MIN, QTE_Y_MAX)
        number = rng.randint(1, 3)
        shrink_speed = round(rng.uniform(QTE_MIN_SHRINK_SPEED, QTE_MAX_SHRINK_SPEED), 3)
        targets.append(
            QTETarget(
                x=x,
                y=y,
                number=number,
                button_radius=QTE_BUTTON_RADIUS,
                start_radius=QTE_START_RADIUS,
                current_radius=QTE_START_RADIUS,
                shrink_speed=shrink_speed,
            )
        )
    return QTESequence(targets=targets)


def resolve_target(qte: QTESequence | None, score: int) -> str:
    """Resolve the active QTE button with a 0..100 score and start its between-button feedback pause."""
    if qte is None or qte.summary_active:
        return "failed"
    qte.intro_frames = 0
    target = qte.current_target
    if target is None or target.resolved:
        return "failed"
    clamped = max(0, min(100, int(score)))
    target.resolved = True
    target.score = clamped
    target.tier = classify_qte_tier(clamped)
    target.feedback_frames = QTE_FEEDBACK_FRAMES
    if clamped >= 61:
        audio.play_sfx(SND_CRIT)
    elif clamped >= 21:
        audio.play_sfx(SND_HIT)
    return target.tier


def advance_sequence_after_feedback(combat: CombatSystem) -> bool:
    """Advance to the next QTE button, or finalize the sequence if all buttons are resolved."""
    qte = combat.active_qte
    if qte is None or qte.summary_active:
        return False
    qte.current_index += 1
    if qte.current_index >= len(qte.targets):
        finalize_qte_sequence(combat)
        return True
    return False


def finalize_qte_sequence(combat: CombatSystem) -> dict[str, object]:
    """Calculate the average QTE score across all resolved buttons and apply cumulative tier rewards."""
    qte = combat.active_qte
    if qte is None:
        return {"score": 0, "tier": "failed", "bonuses": []}

    scores = [t.score for t in qte.targets]
    final_score = int(round(sum(scores) / len(scores))) if scores else 0
    final_tier = classify_qte_tier(final_score)
    qte.final_score = final_score
    qte.final_tier = final_tier
    qte.summary_active = True
    qte.summary_frames = QTE_SUMMARY_FRAMES

    bonuses: list[str] = []
    if final_score <= 20:
        bonuses.append(_t("qte_bonus_none"))
    if final_score >= 21:
        combat.qte_next_damage_mitigation = final_score / 100.0
        bonuses.append(_t("qte_bonus_mitigation", pct=final_score))
    if final_score >= 41:
        def_gain = max(1, int(round(combat.player.effective_stats.defense * 0.10)))
        combat.player.combat_def_buff += def_gain
        bonuses.append(_t("qte_bonus_def_up"))
    if final_score >= 61:
        atk_loss = max(1, int(round(combat.enemy.base_stats.attack * 0.10)))
        combat.enemy.base_stats.attack = max(1, combat.enemy.base_stats.attack - atk_loss)
        bonuses.append(_t("qte_bonus_atk_down"))
    if final_score >= 81 and combat.enemy.is_alive and combat.player.is_alive:
        counter_raw = max(1, int(combat.player.effective_stats.attack * 0.50))
        dealt = combat.damage_enemy(counter_raw)
        healed = combat.player.heal(max(1, dealt // 2)) if dealt > 0 else 0
        bonuses.append(_t("qte_bonus_counter", dmg=dealt, heal=healed))
        audio.play_sfx(SND_CRIT)
        combat._evaluate_battle_outcome()

    qte.bonuses_applied = bonuses
    combat.combat_logs.append(
        _t(
            "combat_qte_resolved",
            tier=_t(f"qte_tier_{final_tier}"),
            score=final_score,
            bonuses=", ".join(bonuses),
        )
    )
    return {"score": final_score, "tier": final_tier, "bonuses": bonuses}
