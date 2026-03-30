import random
from collections import Counter
from typing import Optional

from .models import (
    Character, Resource, Tool, ActivePlayerAction, MissionType, MissionName,
    BOAT_PART_ORDER, Player, GameState, Mission, VolcanoCard,
)


def vote_for_mission(player: Player, state: GameState) -> MissionName:
    """
    Return this player's preferred mission, or random if they have no character preference.

    Each character has a priority heuristic (Builder prefers wood-heavy missions,
    Fire Starter prefers fire missions, etc.). When the volcano deck is running low,
    all characters prioritise boat missions regardless of their usual preference.
    If a Panic volcano card is pending, only missions within its participant cap
    are considered.

    Args:
        player: The player casting a vote.
        state:  Current game state (active missions, volcano deck size).

    Returns:
        The preferred MissionName.
    """
    active = state.active_missions
    if state.pending_volcano_card is not None:
        cap = VolcanoCard.catalog[state.pending_volcano_card].max_mission_participants
        if cap is not None:
            valid_missions = [mission_name for mission_name in active if Mission.catalog[mission_name].players_count <= cap]
            if valid_missions:
                active = valid_missions
    urgent = len(state.volcano_deck) <= state.urgent_volcano_threshold
    boat_options = [mission_name for mission_name in active if Mission.catalog[mission_name].mission_type == MissionType.BOAT]

    if urgent and boat_options:
        return random.choice(boat_options)

    if player.character == Character.BUILDER:
        for mission_name in active:
            if Mission.catalog[mission_name].required_resources.get(Resource.WOOD, 0) >= 2:
                return mission_name
    elif player.character == Character.FIRE_STARTER:
        for mission_name in active:
            if Mission.catalog[mission_name].mission_type == MissionType.FIRE:
                return mission_name
    elif player.character == Character.COOK:
        for mission_name in active:
            if Tool.VESSEL in Mission.catalog[mission_name].required_tools:
                return mission_name
    elif player.character == Character.SAILOR:
        if boat_options:
            return random.choice(boat_options)

    return random.choice(active)


def get_next_needed_boat_part(state: GameState) -> Optional[MissionName]:
    """
    Return the first boat part in BOAT_PART_ORDER that is reachable but not yet built.

    A boat part is considered reachable if it exists in the active missions, the mission
    pool, or has already been built (i.e. it is part of this game's boat part set).
    This filters out parts like FIT_THE_RUDDER that may not be in shorter games.

    Args:
        state: Current game state.

    Returns:
        The next needed MissionName, or None if all reachable boat parts are built.
    """
    reachable = set(state.active_missions) | set(state.mission_pool) | state.boat_parts_built
    for mission_name in BOAT_PART_ORDER:
        if mission_name in reachable and mission_name not in state.boat_parts_built:
            return mission_name
    return None


def decide_active_player_action(active_player: Player, state: GameState) -> ActivePlayerAction:
    """
    Decide whether the active player runs a mission or shuffles the mission deck.

    Since shuffling draws a volcano card, the agent avoids shuffling when the
    volcano deck is at or below the urgent threshold.

    Decision rules in order:
    1. Required shuffle: all active missions are boat parts AND the next needed boat
       part is not among them → SHUFFLE_MISSIONS (mandatory), unless the volcano
       deck is urgent (attempt a mission instead to avoid a guaranteed volcano draw).
    2. No boat parts visible and volcano deck is not urgent: 25 % chance to
       voluntarily shuffle (low probability because shuffling now draws a volcano card).
    3. Otherwise → CHOOSE_MISSION.

    If SHUFFLE_MISSIONS would be chosen but the active player has no resources to pay
    the cost, falls back to CHOOSE_MISSION.

    Args:
        active_player: The player whose turn it is to lead this round.
        state:         Current game state.

    Returns:
        The chosen ActivePlayerAction.
    """
    volcano_is_urgent = len(state.volcano_deck) <= state.urgent_volcano_threshold

    active_boat_missions = [
        mission_name for mission_name in state.active_missions
        if Mission.catalog[mission_name].mission_type == MissionType.BOAT
    ]
    all_active_are_boat_parts = len(active_boat_missions) == len(state.active_missions)
    next_needed = get_next_needed_boat_part(state)
    next_needed_not_active = next_needed not in state.active_missions

    if all_active_are_boat_parts and next_needed_not_active:
        if active_player.resources and not volcano_is_urgent:
            return ActivePlayerAction.SHUFFLE_MISSIONS
        return ActivePlayerAction.CHOOSE_MISSION

    no_boat_parts_visible = len(active_boat_missions) == 0
    if no_boat_parts_visible and not volcano_is_urgent:
        if active_player.resources and random.random() < 0.25:
            return ActivePlayerAction.SHUFFLE_MISSIONS

    return ActivePlayerAction.CHOOSE_MISSION


def select_participants(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
    """
    Select participants for the mission, preferring players with more resources.

    The active player is always selected first if they are in the preferred pool
    (2+ resources and not exhausted). Remaining slots are filled from the preferred
    pool (randomly), then the fallback pool (1 resource, randomly). Players with
    0 resources or exhausted players are excluded entirely.

    Args:
        active_player: The active player this round (prioritized in the preferred pool).
        mission:       The mission to staff.
        state:         Current game state.

    Returns:
        A list of up to mission.players_count Player objects.
    """
    needed = mission.players_count

    active_is_preferred = not active_player.is_exhausted and len(active_player.resources) >= 2

    preferred = [player for player in state.players if player is not active_player and not player.is_exhausted and len(player.resources) >= 2]
    fallback = [player for player in state.players if not player.is_exhausted and len(player.resources) == 1]

    random.shuffle(preferred)
    random.shuffle(fallback)

    if active_is_preferred:
        preferred = [active_player] + preferred

    selected = preferred[:needed]
    if len(selected) < needed:
        remaining_slots = needed - len(selected)
        selected = selected + fallback[:remaining_slots]

    return selected


def choose_gather_amount(player: Player) -> int:
    if player.character == Character.GATHERER and not player.is_exhausted and len(player.resources) < 3:
        return 2

    return 1
