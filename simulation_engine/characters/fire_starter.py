from typing import Optional

from .base import CharacterStrategy
from ..models import Character, MissionType, MissionName, Mission, MissionRequirement


class FireStarterStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.FIRE_STARTER

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        preferred = [
            mission_name for mission_name in active_missions
            if Mission.catalog[mission_name].mission_type == MissionType.FIRE
        ]
        if not preferred:
            return None
        return max(preferred, key = lambda mission_name: Mission.catalog[mission_name].points)

    def requirement_discount(self, mission: Mission, requirements: MissionRequirement) -> MissionRequirement:
        if mission.mission_type == MissionType.FIRE:
            return MissionRequirement(typed = requirements.typed, any_extra = requirements.any_extra - 1)

        return requirements

    def mission_success_bonus_points(self, mission: Mission) -> int:
        return 1 if mission.mission_type == MissionType.FIRE else 0
