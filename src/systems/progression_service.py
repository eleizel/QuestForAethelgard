"""Domain service managing hero level progression, affinity scoring, and class promotions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from src.core.commands import CommandResult
from src.core.events import AudioCue, event_bus

if TYPE_CHECKING:
    from src.entities.player import Player


class ProgressionService:
    """Stateless domain service managing character promotion and affinity calculation."""

    @staticmethod
    def get_recommended_promotion(player: Player) -> str:
        """Calculate the best-fit advanced class based on current ability affinities."""
        promotions = player.available_promotions()
        if not promotions:
            return ""

        scores = {class_id: 0 for class_id in promotions}
        for ability in (*player.abilities.active, *player.abilities.passive):
            for class_id in promotions:
                scores[class_id] += ability.affinities.count(class_id)

        return max(promotions, key=lambda cid: (scores[cid], -promotions.index(cid)))

    @staticmethod
    def promote_class(player: Player, class_id: str, bus=event_bus) -> CommandResult:
        """Execute class promotion and trigger victory fanfare."""
        if player.promote(class_id):
            bus.emit_audio(AudioCue.VICTORY)
            return CommandResult(
                success=True,
                message=f"Promoted to {class_id}",
                payload={"class_id": class_id},
            )

        return CommandResult(
            success=False,
            error_code="PROMOTION_FAILED",
            message="Promotion failed or requirements not met",
        )
