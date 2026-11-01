"""Domain service encapsulating merchant transactions, pouch validation, and pricing."""

from __future__ import annotations

from typing import TYPE_CHECKING
from src.core.commands import CommandResult
from src.core.events import AudioCue, event_bus
from src.core.i18n import t
from src.config import MAX_POUCH_SLOTS

if TYPE_CHECKING:
    from src.entities.player import Player
    from src.entities.item import Item


class ShopService:
    """Stateless domain service managing merchant buy/sell rules."""

    @staticmethod
    def calculate_sell_price(item: Item) -> int:
        """Calculate the gold refund for selling an item."""
        return max(5, item.gold_value // 2)

    @classmethod
    def buy_item(
        cls,
        player: Player,
        stock: list[tuple[Item, int]],
        index: int,
        bus=event_bus,
    ) -> CommandResult:
        """Process purchasing an item from merchant stock."""
        if not (0 <= index < len(stock)):
            return CommandResult(success=False, error_code="INVALID_INDEX", message="Invalid item index")

        item, price = stock[index]
        if player.gold < price:
            return CommandResult(
                success=False,
                error_code="NO_GOLD",
                message=t("shop_no_gold"),
            )

        if len(player.inventory.pouch) >= MAX_POUCH_SLOTS:
            return CommandResult(
                success=False,
                error_code="POUCH_FULL",
                message=t("msg_pouch_full"),
            )

        player.gold -= price
        player.inventory.add_to_pouch(item)
        stock.pop(index)

        bus.emit_audio(AudioCue.CLICK)
        return CommandResult(
            success=True,
            message=t("shop_purchased", item=item.localized_name),
            payload={"item": item, "price": price},
        )

    @classmethod
    def sell_item(
        cls,
        player: Player,
        pouch_index: int,
        bus=event_bus,
    ) -> CommandResult:
        """Process selling an item from the player pouch."""
        pouch = player.inventory.pouch
        if not (0 <= pouch_index < len(pouch)):
            return CommandResult(success=False, error_code="INVALID_INDEX", message="Invalid pouch index")

        item = pouch[pouch_index]
        sell_val = cls.calculate_sell_price(item)

        sold_item = player.inventory.remove_from_pouch(pouch_index)
        if not sold_item:
            return CommandResult(success=False, error_code="REMOVE_FAILED", message="Failed to remove item from pouch")

        player.gold += sell_val
        bus.emit_audio(AudioCue.CLICK)
        return CommandResult(
            success=True,
            message=t("shop_sold", item=sold_item.localized_name, val=sell_val),
            payload={"item": sold_item, "val": sell_val},
        )
