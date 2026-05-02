from dataclasses import dataclass, field
from typing import Optional, ClassVar

from .bonus_effects import BonusEffect
from .enums import Resource, Tool, MissionType, MissionName, VolcanoCardName


@dataclass(frozen = True)
class Mission:
    name: MissionName
    required_resources: dict[Resource, int]
    players_count: int
    points: int
    mission_type: MissionType
    required_tools: list[Tool] = field(default_factory = list)
    bonus_on_success: Optional[BonusEffect] = None

    catalog: ClassVar[dict[MissionName, 'Mission']]

    @classmethod
    def get(cls, name: MissionName) -> 'Mission':
        return cls.catalog[name]


Mission.catalog = {
    MissionName.LIGHT_A_FIRE: Mission(
        name = MissionName.LIGHT_A_FIRE,
        required_resources = { Resource.WOOD: 1 },
        players_count = 2,
        points = 2,
        mission_type = MissionType.FIRE,
        bonus_on_success = BonusEffect(participant_card_draws = 1),
    ),
    MissionName.TORCH_FOR_THE_NIGHT: Mission(
        name = MissionName.TORCH_FOR_THE_NIGHT,
        required_resources = { Resource.WOOD: 1, Resource.ROPE: 1 },
        players_count = 3,
        points = 3,
        mission_type = MissionType.FIRE,
        bonus_on_success = BonusEffect(skip_next_complication = True),
    ),
    MissionName.FETCH_WATER: Mission(
        name = MissionName.FETCH_WATER,
        required_resources = { Resource.ROPE: 1, Resource.WOOD: 1 },
        players_count = 3,
        points = 3,
        mission_type = MissionType.FOOD,
        required_tools = [Tool.VESSEL],
        bonus_on_success = BonusEffect(gather_bonus = 1),
    ),
    MissionName.HUNT: Mission(
        name = MissionName.HUNT,
        required_resources = { Resource.STONE: 1, Resource.ROPE: 1 },
        players_count = 3,
        points = 3,
        mission_type = MissionType.FOOD,
        required_tools = [Tool.KNIFE],
        bonus_on_success = BonusEffect(protect_next_failure = True),
    ),
    MissionName.PREPARE_FOOD: Mission(
        name = MissionName.PREPARE_FOOD,
        required_resources = { Resource.WOOD: 1 },
        players_count = 3,
        points = 3,
        mission_type = MissionType.FOOD,
        required_tools = [Tool.KNIFE, Tool.VESSEL],
        bonus_on_success = BonusEffect(no_exhaustion = True),
    ),
    MissionName.BUILD_A_SHELTER: Mission(
        name = MissionName.BUILD_A_SHELTER,
        required_resources = { Resource.WOOD: 1, Resource.STONE: 1 },
        players_count = 4,
        points = 4,
        mission_type = MissionType.SHELTER,
        required_tools = [Tool.KNIFE],
        bonus_on_success = BonusEffect(negates_volcano_card = VolcanoCardName.RAIN_AND_MUD),
    ),
    MissionName.FORTIFY_THE_CAMP: Mission(
        name = MissionName.FORTIFY_THE_CAMP,
        required_resources = { Resource.ROPE: 1 },
        players_count = 2,
        points = 2,
        mission_type = MissionType.SHELTER,
        required_tools = [Tool.KNIFE],
        bonus_on_success = BonusEffect(empty_hand_card_draws = 1),
    ),
    MissionName.GATHER_MATERIALS: Mission(
        name = MissionName.GATHER_MATERIALS,
        required_resources = { Resource.WOOD: 1, Resource.STONE: 1, Resource.ROPE: 1 },
        players_count = 3,
        points = 3,
        mission_type = MissionType.SHELTER,
    ),
    MissionName.CUT_THE_KEEL: Mission(
        name = MissionName.CUT_THE_KEEL,
        required_resources = { Resource.WOOD: 1, Resource.ROPE: 1 },
        players_count = 3,
        points = 1,
        mission_type = MissionType.BOAT,
        required_tools = [Tool.KNIFE],
        bonus_on_success = BonusEffect(boat_part = True),
    ),
    MissionName.ASSEMBLE_THE_HULL: Mission(
        name = MissionName.ASSEMBLE_THE_HULL,
        required_resources = { Resource.WOOD: 1, Resource.STONE: 1 },
        players_count = 3,
        points = 1,
        mission_type = MissionType.BOAT,
        bonus_on_success = BonusEffect(boat_part = True),
    ),
    MissionName.RAISE_THE_MAST: Mission(
        name = MissionName.RAISE_THE_MAST,
        required_resources = { Resource.WOOD: 1, Resource.ROPE: 1 },
        players_count = 3,
        points = 1,
        mission_type = MissionType.BOAT,
        required_tools = [Tool.VESSEL],
        bonus_on_success = BonusEffect(boat_part = True),
    ),
    MissionName.MAKE_THE_SAIL: Mission(
        name = MissionName.MAKE_THE_SAIL,
        required_resources = { Resource.WOOD: 1, Resource.ROPE: 1 },
        players_count = 4,
        points = 1,
        mission_type = MissionType.BOAT,
        bonus_on_success = BonusEffect(boat_part = True),
    ),
    MissionName.FIT_THE_RUDDER: Mission(
        name = MissionName.FIT_THE_RUDDER,
        required_resources = { Resource.WOOD: 1, Resource.ROPE: 1 },
        players_count = 4,
        points = 1,
        mission_type = MissionType.BOAT,
        required_tools = [Tool.VESSEL],
        bonus_on_success = BonusEffect(boat_part = True),
    ),
}
