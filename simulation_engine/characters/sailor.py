from typing import Optional

from ..models import Character, MissionType, MissionName, BOAT_PART_ORDER, Mission
from .base import CharacterStrategy


class SailorStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.SAILOR

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        boat_options = {
            mission_name for mission_name in active_missions
            if Mission.catalog[mission_name].mission_type == MissionType.BOAT
        }
        for boat_name in BOAT_PART_ORDER:
            if boat_name in boat_options:
                return boat_name
        return None

    def complication_draw_count(self, mission: Mission) -> int:
        if mission.mission_type == MissionType.BOAT:
            return 2
        return 1
