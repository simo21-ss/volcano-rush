import random

from .models import (
    ActivePlayerAction, MissionType, MissionName,
    Player, GameState, Mission, VolcanoCard,
)
from .characters import get_strategy


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

    strategy = get_strategy(player.character)
    preferred = strategy.preferred_mission(active)
    if preferred is not None:
        return preferred

    return random.choice(active)


def decide_active_player_action(active_player: Player, state: GameState) -> ActivePlayerAction:
    """
    Decide whether the active player runs a mission or shuffles the mission deck.

    Delegates to the character's strategy. The default strategy avoids shuffling
    when the volcano deck is at or below the urgent threshold.

    Args:
        active_player: The player whose turn it is to lead this round.
        state:         Current game state.

    Returns:
        The chosen ActivePlayerAction.
    """
    strategy = get_strategy(active_player.character)
    return strategy.decide_action(active_player, state)


def select_participants(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
    """
    Select participants for the mission, preferring players with more resources.

    Delegates to the character's strategy. The default strategy selects the active
    player first if preferred, then fills remaining slots from players with 2+
    resources, then falls back to 1-resource players.

    Args:
        active_player: The active player this round (prioritized in the preferred pool).
        mission:       The mission to staff.
        state:         Current game state.

    Returns:
        A list of up to mission.players_count Player objects.
    """
    strategy = get_strategy(active_player.character)
    return strategy.select_participants(active_player, mission, state)


def choose_gather_amount(player: Player) -> int:
    strategy = get_strategy(player.character)
    return strategy.gather_amount(player)
