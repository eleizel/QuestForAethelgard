"""Domain service managing ability draft generation, slot validations, and replacement."""

from __future__ import annotations

import random


from typing import TYPE_CHECKING

from src.core.commands import CommandResult

from src.core.events import AudioCue, event_bus

from src.systems.abilities import AbilityRarity, Ability

from src.data.abilities import get_random_abilities


if TYPE_CHECKING:
    from src.entities.player import Player


class DraftService:
    """Stateless domain service managing ability drafting and learning."""

    @classmethod
    def generate_draft(
        cls, player: Player, count: int = 2, rng: random.Random | None = None
    ) -> list[Ability]:
        """Generate random candidate abilities for the current pending draft token."""

        if not player.pending_ability_choices:
            return []

        pending_rarity = player.pending_ability_choices[0]

        rarity_enum = AbilityRarity.STANDARD if pending_rarity == "STANDARD" else AbilityRarity.EPIC

        known = [a.id for a in player.all_passives + player.abilities.active]

        return get_random_abilities(
            rarity=rarity_enum,
            known_abilities=known,
            player_class=player.class_id,
            count=count,
            rng=rng,
        )

    @classmethod
    def apply_selection(
        cls,
        player: Player,
        chosen: Ability,
        replace_index: int | None = None,
        bus=event_bus,
        consume_token: bool = False,
    ) -> CommandResult:
        """Attempt to add or replace an ability in player's equipped loadout."""

        if replace_index is not None:
            player.abilities.replace_ability(chosen, replace_index)

            if consume_token and player.pending_ability_choices:
                player.pending_ability_choices.pop(0)

            bus.emit_audio(AudioCue.CLICK)

            return CommandResult(
                success=True,
                message=chosen.name,
                payload={"ability": chosen, "replaced_index": replace_index},
            )

        added = player.abilities.add_ability(chosen)

        if added:
            if consume_token and player.pending_ability_choices:
                player.pending_ability_choices.pop(0)

            bus.emit_audio(AudioCue.CLICK)

            return CommandResult(
                success=True,
                message=chosen.name,
                payload={"ability": chosen},
            )

        return CommandResult(
            success=False,
            error_code="REPLACE_REQUIRED",
            message="Ability slot replacement required",
            payload={"ability": chosen},
        )

    @classmethod
    def skip_draft(cls, player: Player, bus=event_bus) -> CommandResult:
        """Discard the active ability draft token without selecting an ability."""

        if player.pending_ability_choices:
            player.pending_ability_choices.pop(0)

        bus.emit_audio(AudioCue.CLICK)

        return CommandResult(success=True, message="Draft skipped")
