"""Domain service managing loot claiming, inventory transfer, and post-battle routing."""

from __future__ import annotations

from typing import TYPE_CHECKING
from src.core.commands import CommandResult
from src.core.events import AudioCue, event_bus
from src.core.game_state import GameMode
from src.core.i18n import t

if TYPE_CHECKING:
    from src.entities.player import Player
    from src.entities.item import Item


class LootService:
    """Stateless domain service managing loot rewards and routing."""

    @classmethod
    def take_item(
        cls,
        player: Player,
        pending_loot: list[Item],
        index: int,
        bus=event_bus,
    ) -> CommandResult:
        """Attempt to claim an item from pending loot into the pouch."""
        if not (0 <= index < len(pending_loot)):
            return CommandResult(success=False, error_code="INVALID_INDEX", message="Invalid loot index")

        item = pending_loot[index]
        if player.inventory.add_to_pouch(item):
            pending_loot.pop(index)
            bus.emit_audio(AudioCue.CHEST)
            return CommandResult(
                success=True,
                message=item.name,
                payload={"item": item},
            )

        return CommandResult(
            success=False,
            error_code="POUCH_FULL",
            message=t("msg_pouch_full"),
        )

    @classmethod
    def take_all(
        cls,
        player: Player,
        pending_loot: list[Item],
        bus=event_bus,
    ) -> CommandResult:
        """Claim as many items as possible from pending loot into pouch."""
        taken_count = 0
        i = 0
        while i < len(pending_loot):
            item = pending_loot[i]
            if player.inventory.add_to_pouch(item):
                pending_loot.pop(i)
                taken_count += 1
            else:
                i += 1

        if taken_count > 0:
            bus.emit_audio(AudioCue.CHEST)

        return CommandResult(
            success=taken_count > 0 or len(pending_loot) == 0,
            payload={"taken": taken_count, "remaining": len(pending_loot)},
        )

    @staticmethod
    def resolve_exit_mode(player: Player) -> GameMode | None:
        """Determine next mode upon exiting rewards (Promotion -> Ability Choice -> Map)."""
        if player.promotion_due and player.available_promotions():
            return GameMode.PROMOTION
        if player.pending_ability_choices:
            return GameMode.ABILITY_CHOICE
        return None
