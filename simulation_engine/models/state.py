from dataclasses import dataclass, field
from typing import Optional
from .enums import Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName
from .cards import BonusEffect


@dataclass
class ToolState:
    damaged:    bool          = False
    repair_due: Optional[int] = None


@dataclass
class Player:
    character:       Character
    resources:       list[Resource] = field(default_factory = list)
    is_exhausted:    bool           = False
    exhausted_until: int            = 0
    score:           int            = 0


@dataclass
class GameState:
    players:                       list[Player]
    active_missions:               list[MissionName]
    resource_deck:                 list[Resource]
    complication_deck:             list[ComplicationCardName]
    volcano_deck:                  list[VolcanoCardName]
    tools:                         dict[Tool, ToolState]
    boat_parts_required:           int
    boat_parts_built:              set[MissionName]          = field(default_factory = set)
    mission_pool:                  list[MissionName]         = field(default_factory = list)
    round:                         int                       = 0
    skip_next_complication:        bool                      = False
    protect_next_failure:          bool                      = False
    pending_volcano_card:          Optional[VolcanoCardName] = None
    pending_bonus:                 Optional[BonusEffect]     = None
    urgent_volcano_threshold:      int                       = 4
    active_player_index:           int                       = 0
    resources_consumed:            dict[Resource, int]       = field(default_factory = dict)
    mission_failures_by_resource:  dict[Resource, int]       = field(default_factory = dict)
    mission_failures_any_extra:    int                       = 0
    mission_failures_tool_damaged: dict[Tool, int]           = field(default_factory = dict)
    tool_repairs:                  dict[Tool, int]           = field(default_factory = dict)


@dataclass(frozen = True)
class MissionRequirement:
    typed:     dict[Resource, int]
    any_extra: int


@dataclass
class GameRecord:
    player_count:                  int
    characters:                    list[Character]
    outcome:                       str
    rounds_played:                 int
    final_scores:                  dict[Character, int]
    boat_parts_built:              int
    boat_parts_required:           int
    volcano_cards_remaining:       int
    resources_consumed:            dict[Resource, int]
    mission_failures_by_resource:  dict[Resource, int]
    mission_failures_any_extra:    int
    mission_failures_tool_damaged: dict[Tool, int]
    tool_repairs:                  dict[Tool, int]
