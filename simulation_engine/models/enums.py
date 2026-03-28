from enum import Enum


class Character(Enum):
    BUILDER       = "builder"
    FIRE_STARTER  = "fire_starter"
    CRAFTSMAN     = "craftsman"
    COOK          = "cook"
    GATHERER      = "gatherer"
    SAILOR        = "sailor"


class Resource(Enum):
    WOOD  = "wood"
    STONE = "stone"
    ROPE  = "rope"


class Tool(Enum):
    KNIFE  = "knife"
    VESSEL = "vessel"


class PlayerAction(Enum):
    PARTICIPATE = "participate"
    GATHER      = "gather"
    REPAIR      = "repair"


class MissionType(Enum):
    FIRE    = "fire"
    SHELTER = "shelter"
    FOOD    = "food"
    BOAT    = "boat"


class MissionName(Enum):
    LIGHT_A_FIRE        = "light_a_fire"
    TORCH_FOR_THE_NIGHT = "torch_for_the_night"
    FETCH_WATER         = "fetch_water"
    BUILD_A_SHELTER     = "build_a_shelter"
    FORTIFY_THE_CAMP    = "fortify_the_camp"
    GATHER_MATERIALS    = "gather_materials"
    HUNT                = "hunt"
    PREPARE_FOOD        = "prepare_food"
    CUT_THE_KEEL        = "cut_the_keel"
    ASSEMBLE_THE_HULL   = "assemble_the_hull"
    RAISE_THE_MAST      = "raise_the_mast"
    MAKE_THE_SAIL       = "make_the_sail"
    FIT_THE_RUDDER      = "fit_the_rudder"


class ComplicationCardName(Enum):
    MOSQUITO_ATTACK = "mosquito_attack"
    WET_WOOD        = "wet_wood"
    COLLAPSED_PATH  = "collapsed_path"
    SLIPPERY_ROCKS  = "slippery_rocks"
    BLUNT_BLADE     = "blunt_blade"
    CRACKED_VESSEL  = "cracked_vessel"
    HEAT_AND_THIRST = "heat_and_thirst"
    NIGHT_ANXIETY   = "night_anxiety"
    CAMP_PANIC      = "camp_panic"
    CALM_BREEZE     = "calm_breeze"
    CLEAR_SKY       = "clear_sky"


class VolcanoCardName(Enum):
    RAIN_AND_MUD   = "rain_and_mud"
    ASH_IN_THE_AIR = "ash_in_the_air"
    TREMOR         = "tremor"
    STORM          = "storm"
    LAVA_FLOW      = "lava_flow"
    PANIC          = "panic"
    COLLAPSE       = "collapse"
    HEAT_WAVE      = "heat_wave"
    SMOKE          = "smoke"
    EARTHQUAKE     = "earthquake"
    ERUPTION       = "eruption"
