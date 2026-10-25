"""Status effect data structures, lifecycle triggers, and factory constructors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.entities.actor import Actor, Stats
    from src.systems.combat import CombatSystem


class StatusType(Enum):
    BUFF = auto()
    DEBUFF = auto()


class StatusTrigger(Enum):
    ON_TICK = auto()       # Evaluated on every combat tick (e.g., DOTs)
    STAT_MOD = auto()      # Dynamically modifies attributes (e.g., Fortify, Haste, Weaken)
    PRE_ACTION = auto()    # Evaluated when action gauge reaches 100 (e.g., Stun)
    POST_HIT = auto()      # Evaluated during attack calculation (e.g., Blind, Vulnerable)


@dataclass
class StatusEffect:
    id: str
    name: str
    badge: str                 # 3-char visual tag: "BRN", "PSN", "BLD", "STN", "BLN", "DEF", "SPD", "WKN", "VUL"
    color: int                 # Pyxel palette index
    status_type: StatusType
    trigger: StatusTrigger
    duration: int              # Remaining combat ticks
    potency: int = 0           # Numeric scale (flat damage, stat delta, % chance)
    on_tick_hook: Callable[[CombatSystem, Actor, StatusEffect], tuple[str, int]] | None = None

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
        )


# --- ON-TICK HOOKS ---

def _hook_burn(combat: CombatSystem, target: Actor, status: StatusEffect) -> tuple[str, int]:
    dmg = target.take_damage(status.potency)
    return f"{target.name} burns for {dmg} fire dmg.", dmg

def _hook_poison(combat: CombatSystem, target: Actor, status: StatusEffect) -> tuple[str, int]:
    dmg = target.take_damage(status.potency)
    return f"{target.name} suffers {dmg} poison dmg.", dmg

def _hook_bleed(combat: CombatSystem, target: Actor, status: StatusEffect) -> tuple[str, int]:
    dmg = target.take_damage(status.potency)
    return f"{target.name} bleeds for {dmg} physical dmg.", dmg


# --- FACTORY CONSTRUCTORS ---

def create_burn(duration: int = 8, potency: int = 2) -> StatusEffect:
    return StatusEffect(
        id="burn", name="Burn", badge="BRN", color=9,  # COLOR_ORANGE
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.ON_TICK,
        duration=duration, potency=potency, on_tick_hook=_hook_burn,
    )

def create_poison(duration: int = 10, potency: int = 2) -> StatusEffect:
    return StatusEffect(
        id="poison", name="Poison", badge="PSN", color=11,  # COLOR_LIME
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.ON_TICK,
        duration=duration, potency=potency, on_tick_hook=_hook_poison,
    )

def create_bleed(duration: int = 6, potency: int = 3) -> StatusEffect:
    return StatusEffect(
        id="bleed", name="Bleed", badge="BLD", color=8,  # COLOR_RED
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.ON_TICK,
        duration=duration, potency=potency, on_tick_hook=_hook_bleed,
    )

def create_stun(duration: int = 1) -> StatusEffect:
    return StatusEffect(
        id="stun", name="Stun", badge="STN", color=10,  # COLOR_YELLOW
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.PRE_ACTION,
        duration=duration, potency=1,
    )

def create_blind(duration: int = 10) -> StatusEffect:
    return StatusEffect(
        id="blind", name="Blind", badge="BLN", color=13,  # COLOR_GRAY
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.POST_HIT,
        duration=duration, potency=50,  # 50% miss chance
    )

def create_fortify(duration: int = 15, defense_boost: int = 5) -> StatusEffect:
    return StatusEffect(
        id="fortify", name="Fortify", badge="DEF", color=6,  # COLOR_LIGHT_BLUE
        status_type=StatusType.BUFF, trigger=StatusTrigger.STAT_MOD,
        duration=duration, potency=defense_boost,
    )

def create_haste(duration: int = 12, speed_boost: int = 4) -> StatusEffect:
    return StatusEffect(
        id="haste", name="Haste", badge="SPD", color=12,  # COLOR_CYAN
        status_type=StatusType.BUFF, trigger=StatusTrigger.STAT_MOD,
        duration=duration, potency=speed_boost,
    )

def create_weaken(duration: int = 10, attack_drop: int = 4) -> StatusEffect:
    return StatusEffect(
        id="weaken", name="Weaken", badge="WKN", color=15,  # COLOR_PEACH
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.STAT_MOD,
        duration=duration, potency=attack_drop,
    )

def create_vulnerable(duration: int = 8) -> StatusEffect:
    return StatusEffect(
        id="vulnerable", name="Vulnerable", badge="VUL", color=14,  # COLOR_PINK
        status_type=StatusType.DEBUFF, trigger=StatusTrigger.POST_HIT,
        duration=duration, potency=30,  # +30% damage taken
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
