from typing import Optional

from ..models import Character, MissionType, MissionName, Mission, MissionRequirement
from .base import CharacterStrategy


class FireStarterStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.FIRE_STARTER

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        for mission_name in active_missions:
            if Mission.catalog[mission_name].mission_type == MissionType.FIRE:
                return mission_name
        return None

    def requirement_discount(
        self,
        mission:      Mission,
        requirements: MissionRequirement,
    ) -> MissionRequirement:
        if mission.mission_type == MissionType.FIRE:
            return MissionRequirement(typed = requirements.typed, any_extra = requirements.any_extra - 1)
        return requirements

    def mission_success_bonus_points(self, mission: Mission) -> int:
        if mission.mission_type == MissionType.FIRE:
            return 1
        return 0
