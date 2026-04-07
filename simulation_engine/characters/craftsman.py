from ..models import Character, Resource, Player, GameState
from .base import CharacterStrategy


class CraftsmanStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.CRAFTSMAN

    def take_gathering_action(
        self,
        player: Player,
        state:  GameState,
    ) -> bool:
        if not player.is_exhausted:
            repairable = [
                tool for tool, tool_state in state.tools.items()
                if tool_state.damaged and tool_state.repair_due is None
            ]
            if repairable and Resource.STONE in player.resources:
                state.tools[repairable[0]].repair_due = state.round + 2
                player.resources.remove(Resource.STONE)
                player.score += 1
                return False
        return True
