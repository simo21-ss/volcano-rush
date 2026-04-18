from dataclasses import dataclass, field

from .contribution import CharacterContribution
from .enums import Character, Resource, Tool, GameOutcome


@dataclass(frozen = True)
class MissionRequirement:
    typed: dict[Resource, int]
    any_extra: int


@dataclass
class GameRecord:
    player_count: int
    characters: list[Character]
    outcome: GameOutcome
    rounds_played: int
    final_scores: dict[Character, int]
    boat_parts_built: int
    boat_parts_required: int
    volcano_cards_remaining: int
    resources_consumed: dict[Resource, int]
    mission_failures_by_resource: dict[Resource, int]
    mission_failures_any_extra: int
    mission_failures_tool_damaged: dict[Tool, int]
    tool_repairs: dict[Tool, int]
    contributions: dict[Character, CharacterContribution] = field(default_factory = dict)
