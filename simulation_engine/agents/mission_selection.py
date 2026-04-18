import random
from typing import Optional

from ..models import (
    MissionType, MissionName, BOAT_PART_ORDER,
    Player, GameState, Mission, VolcanoCard,
)
from ..actions import PlayerAction
from ..characters import get_strategy
from .feasibility import team_can_afford


def decide_mission_action(active_player: Player, state: GameState) -> Optional[PlayerAction]:
    """
    Return PlayerAction.SHUFFLE_MISSIONS when the team is stuck on the wrong boat
    parts: all active missions are boat parts, the next-needed boat part (first
    unbuilt in BOAT_PART_ORDER) is not among them, and the active player can pay
    the shuffle cost. Otherwise return None to signal the default choose-mission
    path.
    """
    all_active_are_boat_parts = all(
        Mission.catalog[mission_name].mission_type == MissionType.BOAT
        for mission_name in state.active_missions
    )
    if not all_active_are_boat_parts:
        return None

    next_needed = next(
        (boat_part for boat_part in BOAT_PART_ORDER if boat_part not in state.boat_parts_built),
        None,
    )
    stuck_on_wrong_boats = (
            active_player.resources
            and next_needed is not None
            and next_needed not in state.active_missions
    )

    return PlayerAction.SHUFFLE_MISSIONS if stuck_on_wrong_boats else None


def vote_for_mission(player: Player, state: GameState) -> Optional[MissionName]:
    """
    Return this player's preferred mission, or None if no mission is available.

    Active missions are first filtered by any Panic participant cap, then by
    team feasibility (falls back to the unfiltered list if nothing is feasible so
    the engine can still progress). Under volcano urgency, if a boat mission is
    feasible the next-needed boat part from BOAT_PART_ORDER is chosen. Otherwise
    the character's own preference is applied, with a random tiebreak as fallback.

    Returns None when there are simply no missions to vote on (an edge case where
    active_missions or the Panic-filtered list is empty); the engine treats this
    as a failed round via handle_panic_cap_round.

    Args:
        player: The player casting a vote.
        state:  Current game state (active missions, volcano deck size).

    Returns:
        The preferred MissionName, or None if no mission can be chosen.
    """
    active = state.active_missions
    if state.pending_volcano_card is not None:
        cap = VolcanoCard.catalog[state.pending_volcano_card].max_mission_participants
        if cap is not None:
            valid_missions = [mission_name for mission_name in active if Mission.catalog[mission_name].players_count <= cap]
            if valid_missions:
                active = valid_missions

    if not active:
        return None

    feasible = [mission_name for mission_name in active if team_can_afford(Mission.catalog[mission_name], state)]
    candidates = feasible if feasible else active

    urgent = len(state.volcano_deck) <= state.urgent_volcano_threshold
    feasible_boats = [mission_name for mission_name in feasible if Mission.catalog[mission_name].mission_type == MissionType.BOAT]

    if urgent and feasible_boats:
        for boat_name in BOAT_PART_ORDER:
            if boat_name in feasible_boats and boat_name not in state.boat_parts_built:
                return boat_name
        return random.choice(feasible_boats)

    strategy = get_strategy(player.character)
    preferred = strategy.preferred_mission(candidates)
    if preferred is not None:
        return preferred

    return random.choice(candidates)
