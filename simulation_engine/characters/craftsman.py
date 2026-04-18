from .base import CharacterStrategy
from ..actions import NonParticipantAction, GatherAction, RepairAction
from ..models import Character, Resource, Player, GameState


class CraftsmanStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.CRAFTSMAN

    def choose_non_participant_action(self, player: Player, state: GameState) -> NonParticipantAction:
        if not player.is_exhausted:
            any_repairable = any(
                tool_state.damaged and tool_state.repair_due is None
                for tool_state in state.tools.values()
            )
            if any_repairable and Resource.STONE in player.resources:
                return RepairAction()

        return GatherAction()
