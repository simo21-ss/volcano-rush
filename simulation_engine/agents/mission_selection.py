import random
from typing import Callable, Optional

from ..models import (
    MissionType, MissionName, VolcanoCardName, BOAT_PART_ORDER,
    Player, GameState, Mission,
)
from ..actions import PlayerAction
from ..characters import get_strategy
from .feasibility import team_can_afford


# A mission selector chooses which active mission the active player attempts.
# vote_for_mission is the default rule-based implementation; a learned policy
# can be substituted by passing a different callable to the engine.
MissionSelector = Callable[[Player, GameState], Optional[MissionName]]


def decide_mission_action(active_player: Player, state: GameState) -> Optional[PlayerAction]:
    """
    Return PlayerAction.SHUFFLE_MISSIONS when the active player should reshuffle
    the mission pool: (a) Panic is pending and all active missions are boat parts
    (boats are banned), or (b) all active missions are boat parts, but the
    next-needed boat part is not among them. Both require the active player to
    have a resource to pay the shuffle cost. Otherwise, return None to signal the
    default choose-mission path.
    """
    all_active_are_boat_parts = all(
        Mission.catalog[mission_name].mission_type == MissionType.BOAT
        for mission_name in state.active_missions
    )
    if not all_active_are_boat_parts:
        return None

    has_shuffle_cost = bool(active_player.resources)

    if VolcanoCardName.PANIC in state.pending_volcano_cards and has_shuffle_cost:
        return PlayerAction.SHUFFLE_MISSIONS

    next_needed = next(
        (boat_part for boat_part in BOAT_PART_ORDER if boat_part not in state.boat_parts_built),
        None,
    )
    stuck_on_wrong_boats = (
            has_shuffle_cost
            and next_needed is not None
            and next_needed not in state.active_missions
    )

    return PlayerAction.SHUFFLE_MISSIONS if stuck_on_wrong_boats else None


def vote_for_mission(player: Player, state: GameState) -> Optional[MissionName]:
    """
    Return this player's preferred mission, or None if no mission can be chosen.

    Active missions are first filtered by any pending Panic card (boat missions
    are banned while Panic is pending), then by team feasibility (falls back to
    the unfiltered list if nothing is feasible so the engine can still progress).
    Under volcano urgency, if a boat mission is feasible the next-needed boat
    part from BOAT_PART_ORDER is chosen. Otherwise the character's own preference
    is applied, with a random tiebreak as fallback.

    Returns None when no mission is legal - under Panic this happens when all
    three active missions are boat parts and the active player had no resource
    to shuffle them away; `run_round` handles that as a forfeited round.

    Args:
        player: The player casting a vote.
        state:  Current game state (active missions, volcano deck size).

    Returns:
        The preferred MissionName, or None if no mission can be chosen.
    """
    active = state.active_missions
    if VolcanoCardName.PANIC in state.pending_volcano_cards:
        active = [mission_name for mission_name in active if Mission.catalog[mission_name].mission_type != MissionType.BOAT]

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
