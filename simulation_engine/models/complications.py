from dataclasses import dataclass, field
from typing import Optional, ClassVar

from .enums import Resource, Tool, ComplicationCardName


@dataclass(frozen = True)
class ComplicationCard:
    name: ComplicationCardName
    severity: int
    extra_resources: dict[Resource, int] = field(default_factory = dict)
    extra_resources_any: int = 0
    extra_per_participant: int = 0
    damages_tool_on_success: Optional[Tool] = None
    requires_extra_helper: bool = False
    max_resource_per_type: Optional[int] = None
    conditional_on_resource: Optional[Resource] = None

    catalog: ClassVar[dict[ComplicationCardName, 'ComplicationCard']]

    @classmethod
    def get(cls, name: ComplicationCardName) -> 'ComplicationCard':
        return cls.catalog[name]


ComplicationCard.catalog = {
    ComplicationCardName.MOSQUITO_ATTACK: ComplicationCard(
        name = ComplicationCardName.MOSQUITO_ATTACK,
        severity = 1,
        extra_resources = { Resource.ROPE: 1 },
    ),
    ComplicationCardName.WET_WOOD: ComplicationCard(
        name = ComplicationCardName.WET_WOOD,
        severity = 1,
        extra_resources = { Resource.WOOD: 1 },
        conditional_on_resource = Resource.WOOD,
    ),
    ComplicationCardName.COLLAPSED_PATH: ComplicationCard(
        name = ComplicationCardName.COLLAPSED_PATH,
        severity = 1,
        extra_resources = { Resource.STONE: 1 },
    ),
    ComplicationCardName.SLIPPERY_ROCKS: ComplicationCard(
        name = ComplicationCardName.SLIPPERY_ROCKS,
        severity = 3,
        extra_resources_any = 2,
    ),
    ComplicationCardName.BLUNT_BLADE: ComplicationCard(
        name = ComplicationCardName.BLUNT_BLADE,
        severity = 2,
        damages_tool_on_success = Tool.KNIFE,
    ),
    ComplicationCardName.CRACKED_VESSEL: ComplicationCard(
        name = ComplicationCardName.CRACKED_VESSEL,
        severity = 2,
        damages_tool_on_success = Tool.VESSEL,
    ),
    ComplicationCardName.HEAT_AND_THIRST: ComplicationCard(
        name = ComplicationCardName.HEAT_AND_THIRST,
        severity = 4,
        extra_per_participant = 1,
    ),
    ComplicationCardName.NIGHT_ANXIETY: ComplicationCard(
        name = ComplicationCardName.NIGHT_ANXIETY,
        severity = 5,
        requires_extra_helper = True,
    ),
    ComplicationCardName.CAMP_PANIC: ComplicationCard(
        name = ComplicationCardName.CAMP_PANIC,
        severity = 3,
        max_resource_per_type = 1,
    ),
    ComplicationCardName.CALM_BREEZE: ComplicationCard(
        name = ComplicationCardName.CALM_BREEZE,
        severity = 0,
    ),
    ComplicationCardName.CLEAR_SKY: ComplicationCard(
        name = ComplicationCardName.CLEAR_SKY,
        severity = 0,
    ),
}
