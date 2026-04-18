from typing import ClassVar

from ..models import Character, Player, GameState
from ..actions import NonParticipantAction, GatherAction
from .base import CharacterStrategy


class GathererStrategy(CharacterStrategy):
    ABILITY_DRAW_AMOUNT: ClassVar[int] = 3
    ABILITY_HAND_CEILING: ClassVar[int] = 3

    @property
    def character(self) -> Character:
        return Character.GATHERER

    def choose_non_participant_action(
        self,
        player: Player,
        state: GameState,
    ) -> NonParticipantAction:
        can_use_ability = not player.is_exhausted and len(player.resources) < self.ABILITY_HAND_CEILING
        if can_use_ability:
            return GatherAction(amount = self.ABILITY_DRAW_AMOUNT, causes_exhaustion = True)
        return GatherAction()
