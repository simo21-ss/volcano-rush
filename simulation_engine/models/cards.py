from dataclasses import dataclass, field
from typing import Optional, ClassVar

from .enums import Resource, Tool, MissionType, MissionName, ComplicationCardName, VolcanoCardName


@dataclass(frozen = True)
class BonusEffect:
    resource_discount:      dict[Resource, int]       = field(default_factory = dict)
    resource_discount_any:  int                       = 0
    skip_next_complication: bool                      = False
    gather_bonus:           int                       = 0
    negates_volcano_card:   Optional[VolcanoCardName] = None
    repair_tool:            bool                      = False
    no_exhaustion:          bool                      = False
    protect_next_failure:   bool                      = False
    boat_part:              bool                      = False


@dataclass(frozen = True)
class Mission:
    name:               MissionName
    required_resources: dict[Resource, int]
    players_count:      int
    points:             int
    mission_type:       MissionType
    required_tools:     list[Tool]            = field(default_factory = list)
    bonus_on_success:   Optional[BonusEffect] = None

    catalog: ClassVar[dict[MissionName, 'Mission']]

    @classmethod
    def get(cls, name: MissionName) -> 'Mission':
        return cls.catalog[name]


Mission.catalog = {
    MissionName.LIGHT_A_FIRE: Mission(
        name               = MissionName.LIGHT_A_FIRE,
        required_resources = {Resource.WOOD: 2, Resource.STONE: 1},
        players_count      = 2,
        points             = 2,
        mission_type       = MissionType.FIRE,
        bonus_on_success   = BonusEffect(resource_discount = {Resource.WOOD: 1}),
    ),
    MissionName.TORCH_FOR_THE_NIGHT: Mission(
        name               = MissionName.TORCH_FOR_THE_NIGHT,
        required_resources = {Resource.WOOD: 2, Resource.ROPE: 1},
        players_count      = 3,
        points             = 3,
        mission_type       = MissionType.FIRE,
        bonus_on_success   = BonusEffect(skip_next_complication = True),
    ),
    MissionName.FETCH_WATER: Mission(
        name               = MissionName.FETCH_WATER,
        required_resources = {Resource.ROPE: 2, Resource.WOOD: 1},
        players_count      = 3,
        points             = 3,
        mission_type       = MissionType.FOOD,
        required_tools     = [Tool.VESSEL],
        bonus_on_success   = BonusEffect(gather_bonus = 1),
    ),
    MissionName.HUNT: Mission(
        name               = MissionName.HUNT,
        required_resources = {Resource.STONE: 2, Resource.ROPE: 2},
        players_count      = 3,
        points             = 3,
        mission_type       = MissionType.FOOD,
        required_tools     = [Tool.KNIFE],
        bonus_on_success   = BonusEffect(protect_next_failure = True),
    ),
    MissionName.PREPARE_FOOD: Mission(
        name               = MissionName.PREPARE_FOOD,
        required_resources = {Resource.WOOD: 1, Resource.STONE: 1},
        players_count      = 3,
        points             = 3,
        mission_type       = MissionType.FOOD,
        required_tools     = [Tool.KNIFE, Tool.VESSEL],
        bonus_on_success   = BonusEffect(no_exhaustion = True),
    ),
    MissionName.BUILD_A_SHELTER: Mission(
        name               = MissionName.BUILD_A_SHELTER,
        required_resources = {Resource.WOOD: 2, Resource.ROPE: 1, Resource.STONE: 1},
        players_count      = 4,
        points             = 4,
        mission_type       = MissionType.SHELTER,
        required_tools     = [Tool.KNIFE],
        bonus_on_success   = BonusEffect(negates_volcano_card = VolcanoCardName.RAIN_AND_MUD),
    ),
    MissionName.FORTIFY_THE_CAMP: Mission(
        name               = MissionName.FORTIFY_THE_CAMP,
        required_resources = {Resource.ROPE: 2, Resource.WOOD: 1},
        players_count      = 2,
        points             = 2,
        mission_type       = MissionType.SHELTER,
        required_tools     = [Tool.KNIFE],
        bonus_on_success   = BonusEffect(resource_discount_any = 1),
    ),
    MissionName.GATHER_MATERIALS: Mission(
        name               = MissionName.GATHER_MATERIALS,
        required_resources = {Resource.WOOD: 1, Resource.STONE: 2, Resource.ROPE: 2},
        players_count      = 3,
        points             = 2,
        mission_type       = MissionType.SHELTER,
        bonus_on_success   = BonusEffect(repair_tool = True),
    ),
    MissionName.CUT_THE_KEEL: Mission(
        name               = MissionName.CUT_THE_KEEL,
        required_resources = {Resource.WOOD: 3, Resource.ROPE: 2},
        players_count      = 3,
        points             = 1,
        mission_type       = MissionType.BOAT,
        required_tools     = [Tool.KNIFE],
        bonus_on_success   = BonusEffect(boat_part = True),
    ),
    MissionName.ASSEMBLE_THE_HULL: Mission(
        name               = MissionName.ASSEMBLE_THE_HULL,
        required_resources = {Resource.WOOD: 2, Resource.STONE: 2},
        players_count      = 3,
        points             = 1,
        mission_type       = MissionType.BOAT,
        bonus_on_success   = BonusEffect(boat_part = True),
    ),
    MissionName.RAISE_THE_MAST: Mission(
        name               = MissionName.RAISE_THE_MAST,
        required_resources = {Resource.WOOD: 2, Resource.ROPE: 2},
        players_count      = 3,
        points             = 1,
        mission_type       = MissionType.BOAT,
        required_tools     = [Tool.VESSEL],
        bonus_on_success   = BonusEffect(boat_part = True),
    ),
    MissionName.MAKE_THE_SAIL: Mission(
        name               = MissionName.MAKE_THE_SAIL,
        required_resources = {Resource.WOOD: 2, Resource.ROPE: 3},
        players_count      = 2,
        points             = 1,
        mission_type       = MissionType.BOAT,
        bonus_on_success   = BonusEffect(boat_part = True),
    ),
    MissionName.FIT_THE_RUDDER: Mission(
        name               = MissionName.FIT_THE_RUDDER,
        required_resources = {Resource.WOOD: 3, Resource.STONE: 1, Resource.ROPE: 3},
        players_count      = 4,
        points             = 1,
        mission_type       = MissionType.BOAT,
        required_tools     = [Tool.VESSEL],
        bonus_on_success   = BonusEffect(boat_part = True),
    ),
}


@dataclass(frozen = True)
class ComplicationCard:
    name:                    ComplicationCardName
    severity:                int
    extra_resources:         dict[Resource, int]  = field(default_factory = dict)
    extra_resources_any:     int                  = 0
    extra_per_participant:   int                  = 0
    damages_tool_on_success: Optional[Tool]       = None
    requires_extra_helper:   bool                 = False
    max_resource_per_type:   Optional[int]        = None
    conditional_on_resource: Optional[Resource]   = None

    catalog: ClassVar[dict[ComplicationCardName, 'ComplicationCard']]

    @classmethod
    def get(cls, name: ComplicationCardName) -> 'ComplicationCard':
        return cls.catalog[name]


ComplicationCard.catalog = {
    ComplicationCardName.MOSQUITO_ATTACK: ComplicationCard(
        name            = ComplicationCardName.MOSQUITO_ATTACK,
        severity        = 1,
        extra_resources = {Resource.ROPE: 1},
    ),
    ComplicationCardName.WET_WOOD: ComplicationCard(
        name                    = ComplicationCardName.WET_WOOD,
        severity                = 1,
        extra_resources         = {Resource.WOOD: 1},
        conditional_on_resource = Resource.WOOD,
    ),
    ComplicationCardName.COLLAPSED_PATH: ComplicationCard(
        name            = ComplicationCardName.COLLAPSED_PATH,
        severity        = 1,
        extra_resources = {Resource.STONE: 1},
    ),
    ComplicationCardName.SLIPPERY_ROCKS: ComplicationCard(
        name                = ComplicationCardName.SLIPPERY_ROCKS,
        severity            = 3,
        extra_resources_any = 2,
    ),
    ComplicationCardName.BLUNT_BLADE: ComplicationCard(
        name                    = ComplicationCardName.BLUNT_BLADE,
        severity                = 2,
        damages_tool_on_success = Tool.KNIFE,
    ),
    ComplicationCardName.CRACKED_VESSEL: ComplicationCard(
        name                    = ComplicationCardName.CRACKED_VESSEL,
        severity                = 2,
        damages_tool_on_success = Tool.VESSEL,
    ),
    ComplicationCardName.HEAT_AND_THIRST: ComplicationCard(
        name                  = ComplicationCardName.HEAT_AND_THIRST,
        severity              = 4,
        extra_per_participant = 1,
    ),
    ComplicationCardName.NIGHT_ANXIETY: ComplicationCard(
        name                  = ComplicationCardName.NIGHT_ANXIETY,
        severity              = 5,
        requires_extra_helper = True,
    ),
    ComplicationCardName.CAMP_PANIC: ComplicationCard(
        name                  = ComplicationCardName.CAMP_PANIC,
        severity              = 3,
        max_resource_per_type = 1,
    ),
    ComplicationCardName.CALM_BREEZE: ComplicationCard(
        name     = ComplicationCardName.CALM_BREEZE,
        severity = 0,
    ),
    ComplicationCardName.CLEAR_SKY: ComplicationCard(
        name     = ComplicationCardName.CLEAR_SKY,
        severity = 0,
    ),
}


@dataclass(frozen = True)
class VolcanoCard:
    name:                        VolcanoCardName
    extra_resources:             dict[Resource, int]  = field(default_factory = dict)
    conditional_on_resource:     Optional[Resource]   = None
    extra_exhaustion_rounds:     int                  = 0
    discard_mission:             bool                 = False
    each_player_loses_resources: int                  = 0
    max_mission_participants:    Optional[int]        = None
    rich_player_loses_threshold: Optional[int]        = None
    gather_yields_zero:          bool                 = False
    mission_point_penalty:       int                  = 0
    extend_exhaustion_rounds:    int                  = 0
    is_eruption:                 bool                 = False

    catalog: ClassVar[dict[VolcanoCardName, 'VolcanoCard']]

    @classmethod
    def get(cls, name: VolcanoCardName) -> 'VolcanoCard':
        return cls.catalog[name]


VolcanoCard.catalog = {
    VolcanoCardName.RAIN_AND_MUD:   VolcanoCard(name = VolcanoCardName.RAIN_AND_MUD, extra_resources = {Resource.WOOD: 2}, conditional_on_resource = Resource.WOOD),
    VolcanoCardName.ASH_IN_THE_AIR: VolcanoCard(name = VolcanoCardName.ASH_IN_THE_AIR, extra_exhaustion_rounds = 1),
    VolcanoCardName.TREMOR:         VolcanoCard(name = VolcanoCardName.TREMOR, discard_mission = True),
    VolcanoCardName.STORM:          VolcanoCard(name = VolcanoCardName.STORM, each_player_loses_resources = 1),
    VolcanoCardName.LAVA_FLOW:      VolcanoCard(name = VolcanoCardName.LAVA_FLOW, extra_resources = {Resource.ROPE: 1}),
    VolcanoCardName.PANIC:          VolcanoCard(name = VolcanoCardName.PANIC, max_mission_participants = 3),
    VolcanoCardName.COLLAPSE:       VolcanoCard(name = VolcanoCardName.COLLAPSE, each_player_loses_resources = 1, rich_player_loses_threshold = 3),
    VolcanoCardName.HEAT_WAVE:      VolcanoCard(name = VolcanoCardName.HEAT_WAVE, gather_yields_zero = True),
    VolcanoCardName.SMOKE:          VolcanoCard(name = VolcanoCardName.SMOKE, mission_point_penalty = 1),
    VolcanoCardName.EARTHQUAKE:     VolcanoCard(name = VolcanoCardName.EARTHQUAKE, extend_exhaustion_rounds = 1),
    VolcanoCardName.ERUPTION:       VolcanoCard(name = VolcanoCardName.ERUPTION, is_eruption = True),
}
