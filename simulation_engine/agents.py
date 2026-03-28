import random
import math
import numpy as np
from collections import Counter
from typing import Optional

from .models import (
    Character, Resource, Tool, PlayerAction, MissionType, MissionName,
    Player, GameState, Mission, VolcanoCard, RESOURCE_INDEX,
)
from .initialization import URGENT_VOLCANO_THRESHOLD


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
    urgent = len(state.volcano_deck) <= URGENT_VOLCANO_THRESHOLD
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

    return np.random.choice(active)


def select_mission(state: GameState) -> Optional[MissionName]:
    """
    Aggregate all player votes and return the mission with the most support.

    Players with no preference contribute a random vote. Ties are broken randomly.
    If a Panic volcano card is pending and no active mission fits within the
    participant cap, returns None to signal that the round has no valid mission.

    Args:
        state: Current game state (players, active missions).

    Returns:
        The selected MissionName for this round, or None if no mission fits the Panic cap.
    """
    if state.pending_volcano_card is not None:
        cap = VolcanoCard.catalog[state.pending_volcano_card].max_mission_participants
        if cap is not None:
            valid_missions = [mission_name for mission_name in state.active_missions if Mission.catalog[mission_name].players_count <= cap]
            if not valid_missions:
                return None

    votes = Counter(vote_for_mission(player, state) for player in state.players)
    max_votes = max(votes.values())
    top_missions = [mission_name for mission_name, vote_count in votes.items() if vote_count == max_votes]

    return random.choice(top_missions)


def decide_action(
    player:                    Player,
    mission:                   Mission,
    current_participant_count: int,
    state:                     GameState,
) -> PlayerAction:
    """
    Decide what action a player takes this round: participate, gather, or repair.

    Priority order:
    1. Craftsman repairs a damaged tool if they have stone and a slot is available.
    2. Exhausted players always gather.
    3. Players with ≤ 1 resource gather (conservation, unless urgent).
    4. Players avoid piling on when >50% of the group is exhausted (unless urgent).
    5. Players participate if they can cover their share and keep at least 1 resource.
    6. Otherwise gather.

    Args:
        player:                    The player deciding.
        mission:                   The selected mission for this round.
        current_participant_count: Number of players already committed to the mission.
        state:                     Current game state (tools, players, volcano deck).

    Returns:
        The chosen PlayerAction.
    """
    urgent = len(state.volcano_deck) <= URGENT_VOLCANO_THRESHOLD

    # Craftsman: repair if tool damaged and no repair already in progress
    if player.character == Character.CRAFTSMAN and not player.is_exhausted:
        repairable = [
            tool for tool, tool_state in state.tools.items()
            if tool_state.damaged and tool_state.repair_due is None
        ]
        if repairable and player.resources[RESOURCE_INDEX[Resource.STONE]] > 0:
            return PlayerAction.REPAIR

    if player.is_exhausted:
        return PlayerAction.GATHER

    # Low-pressure conservation: 1 card in hand → gather
    if not urgent and player.resources.sum() <= 1:
        return PlayerAction.GATHER

    # Exhaustion spreading: >50% exhausted and mission already has enough participants
    if not urgent:
        exhausted_count = sum(1 for p in state.players if p.is_exhausted)
        if exhausted_count > len(state.players) / 2:
            if current_participant_count == mission.players_count:
                return PlayerAction.GATHER

    # Participation check: can contribute share and keep ≥ 1 card
    total_requirements = sum(mission.required_resources.values())
    share = math.ceil(total_requirements / mission.players_count)
    if player.resources.sum() > share:
        return PlayerAction.PARTICIPATE

    return PlayerAction.GATHER


def choose_gather_amount(player: Player) -> int:
    if player.character == Character.GATHERER and not player.is_exhausted and player.resources.sum() < 3:
        return 2

    return 1
