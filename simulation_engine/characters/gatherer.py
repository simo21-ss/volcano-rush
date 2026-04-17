from ..models import Character, Player
from .base import CharacterStrategy


class GathererStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.GATHERER

    def gather_amount(self, player: Player) -> int:
        if not player.is_exhausted and len(player.resources) < 3:
            return 3
        return 1

    def post_gather_exhaustion(self, base_amount: int) -> bool:
        return base_amount == 3
