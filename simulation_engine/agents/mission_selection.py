import random
from typing import ClassVar, Optional

from ..models import (
    MissionType, MissionName, BOAT_PART_ORDER,
    Player, GameState, Mission, VolcanoCard,
)
from ..actions import PlayerAction, ActivePlayerAction
from ..characters import get_strategy
from .feasibility import team_can_afford


def _get_next_needed_boat_part(state: GameState) -> Optional[MissionName]:
    reachable = set(state.active_missions) | set(state.mission_pool) | state.boat_parts_built
    for mission_name in BOAT_PART_ORDER:
        if mission_name in reachable and mission_name not in state.boat_parts_built:
            return mission_name
    return None


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
    as a failed round via _handle_panic_cap_round.

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


def decide_mission_action(active_player: Player, state: GameState) -> PlayerAction:
    """
    Decide whether the active player runs a mission or shuffles the mission deck.

    Shuffles only when all three active missions are boat parts but the next-needed
    boat part is not among them. In that case progress toward the boat is impossible
    so the pool must be refreshed. Shuffling requires the active player to have a
    resource to pay and only runs when the volcano deck is not at the urgent threshold.

    Shuffling to escape a round where no mission is feasible turns out to be worse
    than attempting one: failed missions consume no resources (resolve_mission
    returns before deduction), so the only cost of a failed attempt is one volcano
    draw plus exhaustion. Shuffling costs the same volcano draw plus one resource
    permanently burned from the active player's hand.

    Args:
        active_player: The player whose turn it is to lead this round.
        state:         Current game state.

    Returns:
        The chosen PlayerAction (CHOOSE_MISSION or SHUFFLE_MISSIONS).
    """
    volcano_is_urgent = len(state.volcano_deck) <= state.urgent_volcano_threshold
    has_shuffle_cost = bool(active_player.resources)

    active_boat_missions = [
        mission_name for mission_name in state.active_missions
        if Mission.catalog[mission_name].mission_type == MissionType.BOAT
    ]
    all_active_are_boat_parts = len(active_boat_missions) == len(state.active_missions)
    next_needed = _get_next_needed_boat_part(state)
    next_needed_not_active = next_needed not in state.active_missions

    if all_active_are_boat_parts and next_needed_not_active:
        if has_shuffle_cost and not volcano_is_urgent:
            return PlayerAction.SHUFFLE_MISSIONS

    return PlayerAction.CHOOSE_MISSION


class ChooseMissionAction(ActivePlayerAction):
    action_type: ClassVar[PlayerAction] = PlayerAction.CHOOSE_MISSION

    def execute(self, active_player: Player, state: GameState) -> Optional[MissionName]:
        mission_name = vote_for_mission(active_player, state)
        if mission_name is not None:
            pending_is_panic = (
                state.pending_volcano_card is not None
                and VolcanoCard.get(state.pending_volcano_card).max_mission_participants is not None
            )
            if pending_is_panic:
                state.pending_volcano_card = None
        return mission_name
