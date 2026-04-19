from typing import ClassVar, Optional

from .base import CharacterStrategy
from ..models import Character, MissionType, MissionName, BOAT_PART_ORDER, Mission


class SailorStrategy(CharacterStrategy):
    BOAT_COMPLICATION_DRAWS: ClassVar[int] = 2

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
            return self.BOAT_COMPLICATION_DRAWS

        return super().complication_draw_count(mission)

    def has_active_ability_on(self, mission: Mission) -> bool:
        return mission.mission_type == MissionType.BOAT
