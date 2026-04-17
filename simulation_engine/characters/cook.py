from typing import Optional

from ..models import Character, MissionType, MissionName, Mission
from .base import CharacterStrategy


class CookStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.COOK

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        for mission_name in active_missions:
            if Mission.catalog[mission_name].mission_type == MissionType.FOOD:
                return mission_name
        return None

    def mission_success_bonus_points(self, mission: Mission) -> int:
        if mission.mission_type == MissionType.FOOD:
            return 1
        return 0
