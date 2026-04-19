from abc import ABC, abstractmethod
from typing import Optional

from ..models import (
    Character, MissionName, Player, GameState, Mission, MissionRequirement,
)
from ..actions import NonParticipantAction, GatherAction


class CharacterStrategy(ABC):

    @property
    @abstractmethod
    def character(self) -> Character:
        ...

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        return None

    def choose_non_participant_action(self, player: Player, state: GameState) -> NonParticipantAction:
        return GatherAction()

    def requirement_discount(self, mission: Mission, requirements: MissionRequirement) -> MissionRequirement:
        return requirements

    def complication_draw_count(self, mission: Mission) -> int:
        return 1

    def mission_success_bonus_points(self, mission: Mission) -> int:
        return 0

    def has_active_ability_on(self, mission: Mission) -> bool:
        """
        Return True when this character's ability is relevant to the given mission.
        Used by participant selection to prefer characters whose abilities would
        meaningfully help (requirement discount, mission-success bonus points, or
        lesser-evil complication draws).
        """
        return False
