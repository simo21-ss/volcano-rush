from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .enums import Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName
from .cards import BonusEffect


@dataclass
class ToolState:
    damaged:    bool          = False
    repair_due: Optional[int] = None


@dataclass
class Player:
    character:       Character
    resources:       np.ndarray = field(default_factory = lambda: np.zeros(3, dtype = np.int32))
    is_exhausted:    bool       = False
    exhausted_until: int        = 0
    score:           int        = 0


@dataclass
class GameState:
    players:                list[Player]
    active_missions:        list[MissionName]
    resource_deck:          list[Resource]
    complication_deck:      list[ComplicationCardName]
    volcano_deck:           list[VolcanoCardName]
    tools:                  dict[Tool, ToolState]
    boat_parts_required:    int
    boat_parts_built:       set[MissionName]            = field(default_factory = set)
    mission_pool:           list[MissionName]           = field(default_factory = list)
    round:                  int                         = 0
    skip_next_complication: bool                        = False
    protect_next_failure:   bool                        = False
    pending_volcano_card:   Optional[VolcanoCardName]   = None
    pending_bonus:          Optional[BonusEffect]       = None


@dataclass(frozen = True)
class MissionRequirement:
    typed:     dict[Resource, int]
    any_extra: int


@dataclass
class GameRecord:
    player_count:            int
    characters:              list[Character]
    outcome:                 str
    rounds_played:           int
    final_scores:            dict[Character, int]
    boat_parts_built:        int
    boat_parts_required:     int
    volcano_cards_remaining: int
