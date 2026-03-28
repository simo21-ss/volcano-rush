import random
from typing import Optional
import numpy as np

from .models import (
    Character, Resource, Tool, PlayerAction, MissionType, MissionName, ComplicationCardName,
    GameState, GameRecord, Mission, VolcanoCard, ComplicationCard, RESOURCE_INDEX,
)
from .initialization import init_game
from .deck import draw_resource, draw_complication, draw_volcano, draw_mission
from .mechanics import (
    update_tool_repairs, refresh_exhaustion, apply_exhaustion,
    resolve_mission, apply_volcano_card, apply_bonus,
)
from .agents import select_mission, decide_action, choose_gather_amount


def _handle_volcano_draw(state: GameState) -> bool:
    """
    Draw a volcano card and apply or negate its effect.

    If the drawn card is an eruption, returns True immediately (caller must end
    the game). If state.pending_bonus can negate the card, the bonus is consumed
    and the card has no effect. Otherwise the card is applied via apply_volcano_card.

    Args:
        state: Current game state, mutated in place.

    Returns:
        True if the drawn card is an eruption (game over), False otherwise.
    """
    volcano_card_name = draw_volcano(state)
    if VolcanoCard.get(volcano_card_name).is_eruption:
        return True
    
    if (state.pending_bonus is not None
            and state.pending_bonus.negates_volcano_card == volcano_card_name):
        state.pending_bonus = None
    else:
        apply_volcano_card(volcano_card_name, state)
    
    return False


def _handle_panic_cap_round(state: GameState) -> tuple[list, list, bool, bool, bool]:
    """
    Handle a round where the Panic volcano card prevents any valid mission.

    Clears the pending Panic card, marks the round as a failure with all players
    gathering, and (unless failure is protected) draws a volcano card.

    Args:
        state: Current game state, mutated in place.

    Returns:
        A (participants, gatherers, success, no_exhaustion, eruption) tuple.
        eruption is True if a drawn volcano card is_eruption; the caller must
        return (True, False) immediately in that case.
    """
    state.pending_volcano_card = None
    participants = []
    gatherers = list(state.players)
    success = False
    no_exhaustion = False

    if state.protect_next_failure:
        state.protect_next_failure = False
        eruption = False
    else:
        eruption = _handle_volcano_draw(state)

    return participants, gatherers, success, no_exhaustion, eruption


def _resolve_player_actions(state: GameState, mission: Mission) -> tuple[list, list]:
    """
    Assign each player to participate in, gather during, or repair tools this round.

    Players who choose REPAIR have their stone deducted, queue a tool repair two
    rounds ahead, and join the gatherers list. Players who choose PARTICIPATE join
    participants up to the mission's required count; extras fall back to gathering.

    Args:
        state:   Current game state, mutated in place (tool repair state, resources).
        mission: The selected mission for this round.

    Returns:
        A (participants, gatherers) tuple of Player lists.
    """
    participants: list = []
    gatherers: list = []

    for player in state.players:
        action = decide_action(player, mission, len(participants), state)
        if action == PlayerAction.REPAIR:
            repairable = [
                tool for tool, tool_state in state.tools.items()
                if tool_state.damaged and tool_state.repair_due is None
            ]
            state.tools[repairable[0]].repair_due = state.round + 2
            player.resources[RESOURCE_INDEX[Resource.STONE]] -= 1
            gatherers.append(player)
        elif action == PlayerAction.PARTICIPATE:
            if len(participants) < mission.players_count:
                participants.append(player)
            else:
                gatherers.append(player)
        else:
            gatherers.append(player)

    return participants, gatherers


def _draw_complication_card(
    state:        GameState,
    participants: list,
    mission:      Mission,
) -> ComplicationCard:
    """
    Draw the complication card for this round's mission attempt.

    Three cases apply in order:
    1. If skip_next_complication is set, use CALM_BREEZE and clear the flag.
    2. If a Sailor is participating in a boat mission, draw two cards and keep
       the one with lower severity (best outcome for players).
    3. Otherwise draw one card normally.

    Args:
        state:        Current game state, mutated in place (skip_next_complication flag).
        participants: Players committed to the mission this round.
        mission:      The selected mission for this round.

    Returns:
        The ComplicationCard to use for mission resolution.
    """
    if state.skip_next_complication:
        state.skip_next_complication = False
        
        return ComplicationCard.get(ComplicationCardName.CALM_BREEZE)

    if (any(p.character == Character.SAILOR for p in participants)
            and mission.mission_type == MissionType.BOAT):
        first_complication_name = draw_complication(state)
        second_complication_name = draw_complication(state)
        first_complication_card = ComplicationCard.get(first_complication_name)
        second_complication_card = ComplicationCard.get(second_complication_name)
        
        return (first_complication_card
                if first_complication_card.severity <= second_complication_card.severity
                else second_complication_card)

    return ComplicationCard.get(draw_complication(state))


def _apply_mission_success(
    state:        GameState,
    mission:      Mission,
    mission_name: MissionName,
    participants: list,
) -> bool:
    """
    Apply scoring and bonus effects after a mission succeeds.

    Computes each participant's adjusted point total (base points plus Fire Starter
    bonus, Cook bonus, minus Smoke penalty), awards the points, clears the Smoke
    volcano card if it applied a penalty, and processes the mission's bonus_on_success.

    Args:
        state:        Current game state, mutated in place.
        mission:      The mission that was completed.
        mission_name: The mission's enum name (used for boat-part registration in apply_bonus).
        participants: Players who contributed to and completed the mission.

    Returns:
        True if participants should skip exhaustion this round (from bonus_on_success),
        False otherwise.
    """
    base_points = mission.points
    fire_bonus = (
        any(p.character == Character.FIRE_STARTER for p in participants)
        and mission.mission_type == MissionType.FIRE
    )
    cook_bonus = (
        any(p.character == Character.COOK for p in participants)
        and Tool.VESSEL in mission.required_tools
    )
    point_penalty = (
        VolcanoCard.get(state.pending_volcano_card).mission_point_penalty
        if state.pending_volcano_card is not None
        else 0
    )

    for player in participants:
        points = base_points + (1 if fire_bonus else 0) + (1 if cook_bonus else 0)
        if point_penalty > 0:
            points = max(0, points - point_penalty)
        player.score += points

    if point_penalty > 0:
        state.pending_volcano_card = None

    return apply_bonus(mission.bonus_on_success, mission_name, state)


def _apply_exhaustion_step(
    state:         GameState,
    participants:  list,
    no_exhaustion: bool,
) -> None:
    """
    Apply exhaustion to mission participants at the end of the mission phase.

    If a pending volcano card carries extra_exhaustion_rounds (Ash in the Air),
    those extra rounds are read and the card is consumed before calling
    apply_exhaustion. The step is skipped entirely when no_exhaustion is True.

    Args:
        state:         Current game state, mutated in place.
        participants:  Players who participated in the mission this round.
        no_exhaustion: If True, skip exhaustion entirely.
    """
    extra_exhaustion = (
        VolcanoCard.get(state.pending_volcano_card).extra_exhaustion_rounds
        if state.pending_volcano_card is not None
        else 0
    )
    if extra_exhaustion > 0:
        state.pending_volcano_card = None
    if not no_exhaustion:
        apply_exhaustion(participants, state.round, extra_rounds = extra_exhaustion)


def _apply_gather_step(state: GameState, gatherers: list) -> None:
    """
    Distribute gathered resources to all players in the gatherers list.

    Checks for a Heat Wave pending volcano card (which zeroes all gathering) and
    reads any gather bonus from state.pending_bonus. Each gatherer draws resources
    equal to their base amount plus the bonus. A Gatherer character who draws 2
    resources is exhausted afterward. Clears state.pending_bonus at the end.

    Args:
        state:     Current game state, mutated in place.
        gatherers: Players who are gathering resources this round.
    """
    gather_yields_zero = (
        VolcanoCard.get(state.pending_volcano_card).gather_yields_zero
        if state.pending_volcano_card is not None
        else False
    )
    if gather_yields_zero:
        state.pending_volcano_card = None

    gather_bonus = state.pending_bonus.gather_bonus if state.pending_bonus else 0

    for player in gatherers:
        if gather_yields_zero:
            continue

        base_amount = choose_gather_amount(player)
        total = base_amount + gather_bonus

        for _ in range(total):
            drawn_resource = draw_resource(state)
            player.resources[RESOURCE_INDEX[drawn_resource]] += 1

        if player.character == Character.GATHERER and base_amount == 2:
            apply_exhaustion([player], state.round)

    state.pending_bonus = None


def run_round(state: GameState) -> tuple[bool, bool]:
    """
    Execute one full round of the game.

    Steps in order:
    1. Mission selection — players vote; the winning mission is selected.
       If a Panic volcano card is pending, only missions within its participant
       cap are eligible. If none qualify, the round fails and a volcano card
       is drawn instead.
    2. Player actions — each player decides to participate, gather, or repair.
    3. Complication — a complication card is drawn (Sailor gets best of two on boat missions).
    4. Resolution — mission is attempted; on success bonuses are applied; on failure a
       volcano card is drawn (eruption ends the game immediately).
    5. Exhaustion — participants are exhausted; Ash in the Air adds an extra round.
    6. Gather — gatherers draw resources; Heat Wave cancels gathering.
    7. Mission maintenance — completed mission is replaced from the pool.

    Args:
        state: Current game state, mutated in place.

    Returns:
        A (game_over, won) tuple. game_over is True when the game ends (win or eruption loss).
    """
    state.round += 1
    update_tool_repairs(state)
    refresh_exhaustion(state)

    # Step 1 — Mission selection
    mission_name = select_mission(state)

    if mission_name is None:
        participants, gatherers, success, no_exhaustion, eruption = _handle_panic_cap_round(state)
        if eruption:
            return True, False
    else:
        mission = Mission.get(mission_name)

        # Clear Panic if it was the pending card
        if (state.pending_volcano_card is not None
                and VolcanoCard.get(state.pending_volcano_card).max_mission_participants is not None):
            state.pending_volcano_card = None

        # Step 2 — Player actions
        participants, gatherers = _resolve_player_actions(state, mission)

        # Step 3 — Complication
        complication = _draw_complication_card(state, participants, mission)

        # Step 4 — Resolution
        success = resolve_mission(state, mission, participants, complication)

        if success:
            no_exhaustion = _apply_mission_success(state, mission, mission_name, participants)
        else:
            no_exhaustion = False
            if state.protect_next_failure:
                state.protect_next_failure = False
            else:
                if _handle_volcano_draw(state):
                    return True, False

        # Step 5 — Exhaustion
        _apply_exhaustion_step(state, participants, no_exhaustion)

    # Step 6 — Gather
    _apply_gather_step(state, gatherers)

    # Step 7 — Mission maintenance
    if success:
        state.active_missions.remove(mission_name)
        new_mission = draw_mission(state)
        if new_mission:
            state.active_missions.append(new_mission)

    # Win check
    if len(state.boat_parts_built) >= state.boat_parts_required:
        return True, True

    return False, False


def run_game(player_count: int) -> GameRecord:
    """
    Run a single complete game and return a record of the outcome.

    The game runs for up to 200 rounds. If the round limit is reached without a win
    or eruption, the result is recorded as a loss.

    Args:
        player_count: Number of players (4-8).

    Returns:
        A GameRecord with the outcome, scores, and game statistics.
    """
    state = init_game(player_count)

    for _ in range(200):
        game_over, won = run_round(state)
        if game_over:
            outcome = "win" if won else "loss"
            break
    else:
        outcome = "loss"

    return GameRecord(
        player_count            = player_count,
        characters              = [p.character for p in state.players],
        outcome                 = outcome,
        rounds_played           = state.round,
        final_scores            = {p.character: p.score for p in state.players},
        boat_parts_built        = len(state.boat_parts_built),
        boat_parts_required     = state.boat_parts_required,
        volcano_cards_remaining = len(state.volcano_deck),
    )


def run_scenario(
    player_count: int,
    n_games:      int,
    base_seed:    Optional[int] = None,
) -> list[GameRecord]:
    """
    Run multiple games with the same player count and collect the results.

    Args:
        player_count: Number of players per game (4-8).
        n_games:      Number of games to simulate.
        base_seed:    If provided, seeds each game deterministically (base_seed + game_index)
                      for reproducible results.

    Returns:
        List of GameRecord, one per game.
    """
    results = []
    for i in range(n_games):
        if base_seed is not None:
            random.seed(base_seed + i)
            np.random.seed(base_seed + i)
        results.append(run_game(player_count))

    return results
