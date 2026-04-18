from typing import ClassVar

from ..models import Character, Player
from .base import CharacterStrategy, GatherDecision


class GathererStrategy(CharacterStrategy):
    ABILITY_DRAW_AMOUNT:   ClassVar[int] = 3
    ABILITY_HAND_CEILING:  ClassVar[int] = 3

    @property
    def character(self) -> Character:
        return Character.GATHERER

    def gather(self, player: Player) -> GatherDecision:
        can_use_ability = not player.is_exhausted and len(player.resources) < self.ABILITY_HAND_CEILING
        if can_use_ability:
            return GatherDecision(amount = self.ABILITY_DRAW_AMOUNT, causes_exhaustion = True)
        return GatherDecision(amount = 1)
