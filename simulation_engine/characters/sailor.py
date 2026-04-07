import random
from typing import Optional

from ..models import Character, MissionType, MissionName, Mission
from .base import CharacterStrategy


class SailorStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.SAILOR

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        boat_options = [
            mission_name for mission_name in active_missions
            if Mission.catalog[mission_name].mission_type == MissionType.BOAT
        ]
        if boat_options:
            return random.choice(boat_options)
        return None

    def complication_draw_count(self, mission: Mission) -> int:
        if mission.mission_type == MissionType.BOAT:
            return 2
        return 1
