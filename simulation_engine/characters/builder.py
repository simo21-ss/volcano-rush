from typing import Optional

from ..models import Character, Resource, MissionName, Mission, MissionRequirement
from .base import CharacterStrategy


class BuilderStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.BUILDER

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        preferred = [
            mission_name for mission_name in active_missions
            if Mission.catalog[mission_name].required_resources.get(Resource.WOOD, 0) >= 1
        ]
        if not preferred:
            return None
        return max(preferred, key = lambda mission_name: Mission.catalog[mission_name].points)

    def requirement_discount(self, mission: Mission, requirements: MissionRequirement) -> MissionRequirement:
        if requirements.typed.get(Resource.WOOD, 0) >= 1:
            updated = dict(requirements.typed)
            updated[Resource.WOOD] -= 1
            return MissionRequirement(typed = updated, any_extra = requirements.any_extra)

        return requirements

    def has_active_ability_on(self, mission: Mission) -> bool:
        return mission.required_resources.get(Resource.WOOD, 0) >= 1
