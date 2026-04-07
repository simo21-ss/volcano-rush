from typing import Optional

from ..models import Character, Tool, MissionName, Mission
from .base import CharacterStrategy


class CookStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.COOK

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        for mission_name in active_missions:
            if Tool.VESSEL in Mission.catalog[mission_name].required_tools:
                return mission_name
        return None

    def mission_success_bonus_points(self, mission: Mission) -> int:
        if Tool.VESSEL in mission.required_tools:
            return 1
        return 0
