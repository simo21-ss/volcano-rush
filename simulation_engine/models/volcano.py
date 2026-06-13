from dataclasses import dataclass, field
from typing import Optional, ClassVar

from .enums import Resource, VolcanoCardName


@dataclass(frozen = True)
class VolcanoCard:
    name: VolcanoCardName
    is_immediate: bool = False
    extra_resources: dict[Resource, int] = field(default_factory = dict)
    conditional_on_resource: Optional[Resource] = None
    extra_exhaustion_rounds: int = 0
    discard_mission: bool = False
    each_player_loses_resources: int = 0
    rich_player_loses_threshold: Optional[int] = None
    gather_yields_zero: bool = False
    mission_point_penalty: int = 0
    extend_exhaustion_rounds: int = 0
    is_eruption: bool = False

    catalog: ClassVar[dict[VolcanoCardName, 'VolcanoCard']]

    @classmethod
    def get(cls, name: VolcanoCardName) -> 'VolcanoCard':
        return cls.catalog[name]


VolcanoCard.catalog = {
    VolcanoCardName.RAIN_AND_MUD: VolcanoCard(name = VolcanoCardName.RAIN_AND_MUD, is_immediate = False, extra_resources = { Resource.WOOD: 2 }, conditional_on_resource = Resource.WOOD),
    VolcanoCardName.ASH_IN_THE_AIR: VolcanoCard(name = VolcanoCardName.ASH_IN_THE_AIR, is_immediate = False, extra_exhaustion_rounds = 1),
    VolcanoCardName.TREMOR: VolcanoCard(name = VolcanoCardName.TREMOR, is_immediate = True, discard_mission = True),
    VolcanoCardName.STORM: VolcanoCard(name = VolcanoCardName.STORM, is_immediate = True, each_player_loses_resources = 1),
    VolcanoCardName.LAVA_FLOW: VolcanoCard(name = VolcanoCardName.LAVA_FLOW, is_immediate = False, extra_resources = { Resource.ROPE: 1 }),
    VolcanoCardName.PANIC: VolcanoCard(name = VolcanoCardName.PANIC, is_immediate = False),
    VolcanoCardName.COLLAPSE: VolcanoCard(name = VolcanoCardName.COLLAPSE, is_immediate = True, each_player_loses_resources = 1, rich_player_loses_threshold = 3),
    VolcanoCardName.HEAT_WAVE: VolcanoCard(name = VolcanoCardName.HEAT_WAVE, is_immediate = True, gather_yields_zero = True),
    VolcanoCardName.SMOKE: VolcanoCard(name = VolcanoCardName.SMOKE, is_immediate = False, mission_point_penalty = 1),
    VolcanoCardName.EARTHQUAKE: VolcanoCard(name = VolcanoCardName.EARTHQUAKE, is_immediate = True, extend_exhaustion_rounds = 1),
    VolcanoCardName.ERUPTION: VolcanoCard(name = VolcanoCardName.ERUPTION, is_immediate = True, is_eruption = True),
}
