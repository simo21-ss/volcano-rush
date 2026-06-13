"""
Action spaces for the two learned decisions.

Mission selection uses semantic categories rather than active-mission slot
indices. A slot index is non-stationary - slot 0 holds a different mission every
round - so Q-values keyed on it would not generalise. Categories (next-needed
boat part, other boat part, fire, food, shelter) mean the same thing in every
state, which is what a tabular policy needs.

Participant selection is a per-candidate binary include/exclude action; the
top-k selection over candidates lives in the agent, which has the Q-values.
"""

from typing import Optional

from ..models import (
    GameState, Player, Mission, MissionName, MissionType,
    VolcanoCardName, BOAT_PART_ORDER,
)
from ..agents.feasibility import team_can_afford
from .state_encoding import next_needed_boat_part


# Semantic mission-action categories.
MISSION_ACTION_NEXT_BOAT = 0
MISSION_ACTION_OTHER_BOAT = 1
MISSION_ACTION_FIRE = 2
MISSION_ACTION_FOOD = 3
MISSION_ACTION_SHELTER = 4
MISSION_ACTION_CARDINALITY = 5

_CATEGORY_BY_NON_BOAT_TYPE = {
    MissionType.FIRE: MISSION_ACTION_FIRE,
    MissionType.FOOD: MISSION_ACTION_FOOD,
    MissionType.SHELTER: MISSION_ACTION_SHELTER,
}

# Stable tie-break order within a chosen non-boat category.
_MISSION_DEFINITION_ORDER = {mission_name: index for index, mission_name in enumerate(MissionName)}
_BOAT_BUILD_ORDER = {mission_name: index for index, mission_name in enumerate(BOAT_PART_ORDER)}

# Participant selection is a per-candidate binary choice.
PARTICIPANT_ACTION_EXCLUDE = 0
PARTICIPANT_ACTION_INCLUDE = 1
PARTICIPANT_ACTION_CARDINALITY = 2


def legal_missions(active_player: Player, state: GameState) -> list[MissionName]:
    """
    The candidate missions the active player may choose among.

    Mirrors the rule-based vote_for_mission candidate logic: a pending Panic card
    bans boat missions, then the team-feasible subset is preferred, falling back
    to all active missions when none are feasible so the engine can still
    progress. Returns [] when no mission is legal (the round is forfeited).

    The filter is intentionally duplicated here rather than imported from the
    agents package, because the engine and agents must never import this RL
    package (the dependency runs one way only).
    """
    active = list(state.active_missions)
    if VolcanoCardName.PANIC in state.pending_volcano_cards:
        active = [
            mission_name for mission_name in active
            if Mission.catalog[mission_name].mission_type != MissionType.BOAT
        ]
    if not active:
        return []

    feasible = [mission_name for mission_name in active if team_can_afford(Mission.catalog[mission_name], state)]
    return feasible if feasible else active


def encode_mission_action(mission_name: MissionName, state: GameState) -> int:
    """Map a mission to its semantic action category, given the boat build progress."""
    mission = Mission.catalog[mission_name]
    if mission.mission_type == MissionType.BOAT:
        if mission_name == next_needed_boat_part(state):
            return MISSION_ACTION_NEXT_BOAT
        return MISSION_ACTION_OTHER_BOAT
    return _CATEGORY_BY_NON_BOAT_TYPE[mission.mission_type]


def legal_mission_action_indices(active_player: Player, state: GameState) -> list[int]:
    """The sorted, de-duplicated category indices present among the legal missions."""
    candidates = legal_missions(active_player, state)
    return sorted({encode_mission_action(mission_name, state) for mission_name in candidates})


def decode_mission_action(action_index: int, legal: list[MissionName], state: GameState) -> Optional[MissionName]:
    """
    Resolve a chosen category to one concrete legal mission, breaking ties
    deterministically: boats by build order, non-boats by mission definition
    order. Returns None when no legal mission carries the chosen category.
    """
    matching = [
        mission_name for mission_name in legal
        if encode_mission_action(mission_name, state) == action_index
    ]
    if not matching:
        return None

    if action_index in (MISSION_ACTION_NEXT_BOAT, MISSION_ACTION_OTHER_BOAT):
        return min(matching, key = lambda mission_name: _BOAT_BUILD_ORDER.get(mission_name, len(BOAT_PART_ORDER)))
    return min(matching, key = lambda mission_name: _MISSION_DEFINITION_ORDER[mission_name])
