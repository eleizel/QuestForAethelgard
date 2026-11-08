"""Immutable view models decoupling presentations from domain entity internals.

Frontends (Pygame-CE, Pyxel, Headless) query snapshots through GameSession
without directly reading or mutating entity internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StatusViewModel:
    """Read-only snapshot of an active combat status effect."""

    id: str
    name: str
    duration: int
    stacks: int


@dataclass(frozen=True)
class CombatantViewModel:
    """Read-only snapshot of a combatant's stats and current condition."""

    name: str
    current_hp: int
    max_hp: int
    hp_percent: float
    attack: int
    defense: int
    speed: int
    is_alive: bool
    statuses: list[StatusViewModel] = field(default_factory=list)


@dataclass(frozen=True)
class CombatViewModel:
    """Read-only snapshot of an active or concluded battle."""

    hero: CombatantViewModel
    enemy: CombatantViewModel
    turn_count: int
    is_active: bool
    is_qte_active: bool
    result: str
    logs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ShopItemViewModel:
    """Read-only presentation data for an item on sale."""

    index: int
    item_id: str
    name: str
    description: str
    price: int
    item_type: str
    can_afford: bool


@dataclass(frozen=True)
class ShopViewModel:
    """Read-only presentation data for a merchant visit."""

    player_gold: int
    stock: list[ShopItemViewModel]
    pouch_used: int
    pouch_max: int
    can_buy_any: bool


@dataclass(frozen=True)
class LootItemViewModel:
    """Read-only presentation data for a pending loot drop."""

    index: int
    item_id: str
    name: str
    description: str
    gold_value: int
    item_type: str


@dataclass(frozen=True)
class LootViewModel:
    """Read-only presentation data for post-combat loot screen."""

    items: list[LootItemViewModel]
    pouch_used: int
    pouch_max: int
    has_loot: bool
    pouch_has_space: bool


@dataclass(frozen=True)
class MapNodeViewModel:
    """Read-only presentation data for an exploration map node."""

    id: int
    floor: int
    node_type: str
    visited: bool
    available: bool
    outgoing_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class MapViewModel:
    """Read-only presentation data for the exploration spire map."""

    act: int
    floor: int
    biome: str
    current_node_id: int | None
    available_nodes: list[MapNodeViewModel]
    total_floors: int


@dataclass(frozen=True)
class AbilityOptionViewModel:
    """Read-only presentation data for an ability choice candidate."""

    id: str
    name: str
    description: str
    rarity: str
    affinities: list[str]
    cooldown: int


@dataclass(frozen=True)
class AbilityDraftViewModel:
    """Read-only presentation data for an ability draft screen."""

    pending_choices_count: int
    has_pending_draft: bool
    choices: list[AbilityOptionViewModel] = field(default_factory=list)
