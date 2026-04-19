from typing import Optional

from ..models import Character, MissionType, MissionName, Mission
from .base import CharacterStrategy


class CookStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.COOK

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        preferred = [
            mission_name for mission_name in active_missions
            if Mission.catalog[mission_name].mission_type == MissionType.FOOD
        ]
        if not preferred:
            return None

        return max(preferred, key = lambda mission_name: Mission.catalog[mission_name].points)

    def mission_success_bonus_points(self, mission: Mission) -> int:
        if mission.mission_type == MissionType.FOOD:
            return 1

        return 0

    def has_active_ability_on(self, mission: Mission) -> bool:
        return mission.mission_type == MissionType.FOOD
