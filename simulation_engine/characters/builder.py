from typing import Optional

from .base import CharacterStrategy
from ..models import Character, Resource, MissionName, MissionType, Mission, MissionRequirement


class BuilderStrategy(CharacterStrategy):
    _ELIGIBLE_MISSION_TYPES = (MissionType.SHELTER, MissionType.BOAT)

    @property
    def character(self) -> Character:
        return Character.BUILDER

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        preferred = [
            mission_name for mission_name in active_missions
            if self._applies_to(Mission.catalog[mission_name])
        ]
        if not preferred:
            return None
        return max(preferred, key = lambda mission_name: Mission.catalog[mission_name].points)

    def requirement_discount(self, mission: Mission, requirements: MissionRequirement) -> MissionRequirement:
        if not self._applies_to(mission):
            return requirements
        if requirements.typed.get(Resource.WOOD, 0) >= 1:
            updated = dict(requirements.typed)
            updated[Resource.WOOD] -= 1
            return MissionRequirement(typed = updated, any_extra = requirements.any_extra)

        return requirements

    def has_active_ability_on(self, mission: Mission) -> bool:
        return self._applies_to(mission)

    def _applies_to(self, mission: Mission) -> bool:
        return (
                mission.mission_type in self._ELIGIBLE_MISSION_TYPES
                and mission.required_resources.get(Resource.WOOD, 0) >= 1
        )
