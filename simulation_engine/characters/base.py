from abc import ABC, abstractmethod
from typing import NamedTuple, Optional

from ..models import (
    Character, MissionName, Player, GameState, Mission, MissionRequirement,
)


class GatherDecision(NamedTuple):
    """
    What a character decides to do when the engine invites them to gather resources.

    Attributes:
        amount:             Number of resource cards the player draws from the deck.
        causes_exhaustion:  True if this gather should exhaust the player afterwards
                            (used by the Gatherer when they fire their 3-draw ability).
    """
    amount:            int
    causes_exhaustion: bool = False


class CharacterStrategy(ABC):

    @property
    @abstractmethod
    def character(self) -> Character:
        ...

    # ── Individual player decisions ─────────────────────────────────

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        return None

    def gather(self, player: Player) -> GatherDecision:
        return GatherDecision(amount = 1)

    def take_gathering_action(
        self,
        player: Player,
        state:  GameState,
    ) -> bool:
        return True

    # ── Mission participation modifiers ─────────────────────────────

    def requirement_discount(
        self,
        mission:      Mission,
        requirements: MissionRequirement,
    ) -> MissionRequirement:
        return requirements

    def complication_draw_count(self, mission: Mission) -> int:
        return 1

    def mission_success_bonus_points(self, mission: Mission) -> int:
        return 0
