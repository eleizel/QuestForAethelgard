"""Status effect data structures, lifecycle triggers, and factory constructors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.entities.actor import Actor
    from src.systems.combat import CombatSystem


class StatusType(Enum):
    BUFF = auto()
    DEBUFF = auto()


class StatusTrigger(Enum):
    ON_TICK = auto()  # Evaluated on every combat tick (e.g., DOTs)
    STAT_MOD = auto()  # Dynamically modifies attributes (e.g., Fortify, Haste, Weaken)
    PRE_ACTION = auto()  # Evaluated when action gauge reaches 100 (e.g., Stun)
    POST_HIT = auto()  # Evaluated during attack calculation (e.g., Blind, Vulnerable)


@dataclass
class StatusEffect:
    id: str
    name: str
    badge: str  # 3-char visual tag: "BRN", "PSN", "BLD", "STN", "BLN", "DEF", "SPD", "WKN", "VUL"
    color: int  # Pyxel palette index
    status_type: StatusType
    trigger: StatusTrigger
    duration: int  # Remaining combat ticks
    potency: int = 0  # Numeric scale; Burn uses percentage of max HP per stack
    on_tick_hook: Callable[[CombatSystem, Actor, StatusEffect], tuple[str, int]] | None = None
    stacks: int = 1
    max_stacks: int = 1
    stack_tick_counts: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.id == "burn":
            self.stack_tick_counts = (self.stack_tick_counts + [0] * self.stacks)[:self.stacks]

    @property
    def localized_name(self) -> str:
        from src.core.i18n import t
        return t(f"status_{self.id}_name")

    def clone(self, duration_override: int | None = None) -> StatusEffect:
        return StatusEffect(
            id=self.id,
            name=self.name,
            badge=self.badge,
            color=self.color,
            status_type=self.status_type,
            trigger=self.trigger,
            duration=duration_override if duration_override is not None else self.duration,
            potency=self.potency,
            on_tick_hook=self.on_tick_hook,
            stacks=self.stacks,
            max_stacks=self.max_stacks,
            stack_tick_counts=list(self.stack_tick_counts),
        )


# --- ON-TICK HOOKS ---

def _hook_burn(combat: CombatSystem, target: Actor, status: StatusEffect) -> tuple[str, int]:
    """Deal max-HP percentage damage per stack, bypassing defense."""
    from src.core.i18n import t
    damage_per_stack = max(1, target.max_hp * status.potency // 100)
    raw_damage = damage_per_stack * status.stacks
    dmg = min(target.current_hp, raw_damage)
    target.current_hp -= dmg
    return t("status_tick_burn", target=target.name, dmg=dmg), dmg


def _hook_poison(combat: CombatSystem, target: Actor, status: StatusEffect) -> tuple[str, int]:
    from src.core.i18n import t
    # Attack-scaled poison remains mitigated by defense.
    dmg = target.take_damage(status.potency * status.stacks)
    return t("status_tick_poison", target=target.name, dmg=dmg), dmg


def _hook_bleed(combat: CombatSystem, target: Actor, status: StatusEffect) -> tuple[str, int]:
    from src.core.i18n import t
    dmg = target.take_damage(status.potency)
    return t("status_tick_bleed", target=target.name, dmg=dmg), dmg


# --- FACTORY CONSTRUCTORS ---

def create_burn(duration: int = 8, potency: int = 1) -> StatusEffect:
    """Create Burn: potency is max-HP percentage damage per stack and tick."""
    return StatusEffect(
        id="burn", name="Burn", badge="BRN", color=9,  # COLOR_ORANGE
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.ON_TICK,
        duration=duration, potency=potency, on_tick_hook=_hook_burn,
        stacks=1, max_stacks=3,
    )


def create_poison(duration: int = 5, potency: int = 2, max_stacks: int = 1) -> StatusEffect:
    """Create attack-scaled poison; Venomous Accumulation enables stacking."""
    return StatusEffect(
        id="poison", name="Poison", badge="PSN", color=11,  # COLOR_LIME
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.ON_TICK,
        duration=duration, potency=potency, on_tick_hook=_hook_poison,
        stacks=1, max_stacks=max_stacks,
    )


def create_bleed(duration: int = 6, potency: int = 3) -> StatusEffect:
    return StatusEffect(
        id="bleed", name="Bleed", badge="BLD", color=8,  # COLOR_RED
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.ON_TICK,
        duration=duration, potency=potency, on_tick_hook=_hook_bleed,
    )


def create_stun(duration: int = 1, potency: int = 1) -> StatusEffect:
    return StatusEffect(
        id="stun", name="Stun", badge="STN", color=10,  # COLOR_YELLOW
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.PRE_ACTION,
        duration=duration, potency=potency,
    )


def create_blind(duration: int = 10, potency: int = 50) -> StatusEffect:
    return StatusEffect(
        id="blind", name="Blind", badge="BLN", color=13,  # COLOR_GRAY
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.POST_HIT,
        duration=duration, potency=potency,  # 50% miss chance
    )


def create_fortify(duration: int = 15, potency: int = 5) -> StatusEffect:
    return StatusEffect(
        id="fortify", name="Fortify", badge="DEF", color=6,  # COLOR_LIGHT_BLUE
        status_type=StatusType.BUFF, trigger=StatusTrigger.STAT_MOD,
        duration=duration, potency=potency,
    )


def create_haste(duration: int = 12, potency: int = 4) -> StatusEffect:
    return StatusEffect(
        id="haste", name="Haste", badge="SPD", color=12,  # COLOR_CYAN
        status_type=StatusType.BUFF, trigger=StatusTrigger.STAT_MOD,
        duration=duration, potency=potency,
    )


def create_weaken(duration: int = 10, potency: int = 4) -> StatusEffect:
    return StatusEffect(
        id="weaken", name="Weaken", badge="WKN", color=15,  # COLOR_PEACH
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.STAT_MOD,
        duration=duration, potency=potency,
    )


def create_vulnerable(duration: int = 8, potency: int = 30) -> StatusEffect:
    return StatusEffect(
        id="vulnerable", name="Vulnerable", badge="VUL", color=14,  # COLOR_PINK
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.POST_HIT,
        duration=duration, potency=potency,  # +30% damage taken
    )


STATUS_BUILDERS = {
    "burn": create_burn,
    "poison": create_poison,
    "bleed": create_bleed,
    "stun": create_stun,
    "blind": create_blind,
    "fortify": create_fortify,
    "haste": create_haste,
    "weaken": create_weaken,
    "vulnerable": create_vulnerable,
}


def get_status_by_id(status_id: str, **kwargs) -> StatusEffect | None:
    builder = STATUS_BUILDERS.get(status_id)
    return builder(**kwargs) if builder else None
