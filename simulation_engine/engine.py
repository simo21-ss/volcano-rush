import random
from typing import Optional
from .models import (
    ActivePlayerAction, MissionName, ComplicationCardName,
    GameState, GameRecord, Mission, VolcanoCard, ComplicationCard,
)
from .characters import get_strategy
from .initialization import init_game
from .deck import draw_resource, draw_complication, draw_volcano, draw_mission
from .mechanics import (
    update_tool_repairs, refresh_exhaustion, apply_exhaustion,
    resolve_mission, apply_volcano_card, apply_bonus,
)
from .agents import (
    vote_for_mission, choose_gather_amount,
    decide_active_player_action, select_participants,
)


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


def _apply_non_participant_actions(state: GameState, non_participants: list) -> list:
    """
    Determine the actions of players not selected for the mission.

    Craftsman players who are not exhausted, have Stone, and can start a repair
    do so automatically (deducting 1 Stone, scheduling the repair, awarding 1 point).
    All other non-participants, including the repairing Craftsman, gather resources.

    Args:
        state:            Current game state, mutated in place (tool repair state, resources).
        non_participants: Players not selected to participate in the mission.

    Returns:
        The list of gatherers (all non-participants).
    """
    gatherers = []
    for player in non_participants:
        strategy = get_strategy(player.character)
        strategy.non_participant_action(player, state)
        gatherers.append(player)
    return gatherers


def _apply_shuffle_cost(active_player) -> None:
    """
    Deduct one randomly chosen resource from the active player as the shuffle cost.

    Args:
        active_player: The player paying the cost (must have at least 1 resource).
    """
    resource_to_discard = random.choice(active_player.resources)
    active_player.resources.remove(resource_to_discard)


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

    max_draws = max(
        get_strategy(player.character).complication_draw_count(mission)
        for player in participants
    ) if participants else 1

    if max_draws >= 2:
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
    seen_characters = set()
    bonus_points = 0
    for player in participants:
        if player.character not in seen_characters:
            seen_characters.add(player.character)
            bonus_points += get_strategy(player.character).mission_success_bonus_points(mission)

    point_penalty = (
        VolcanoCard.get(state.pending_volcano_card).mission_point_penalty
        if state.pending_volcano_card is not None
        else 0
    )

    for player in participants:
        points = base_points + bonus_points
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
            player.resources.append(draw_resource(state))

        if get_strategy(player.character).post_gather_exhaustion(base_amount):
            apply_exhaustion([player], state.round)

    state.pending_bonus = None


def run_round(state: GameState) -> tuple[bool, bool]:
    """
    Execute one full round of the game.

    Steps in order:
    1. Identify the active player for this round.
    2. Active player decides: shuffle the mission deck or choose a mission.
       - Shuffle: costs 1 resource, reshuffles mission_pool, draws a volcano card
         (eruption ends the game), round ends (no gather).
       - Choose mission: active player picks via their character preference.
         If a Panic volcano card prevents any valid mission, all players gather and
         a volcano card is drawn (eruption ends the game).
    3. Participant selection — active player's choice, preferring players with 2+
       resources over 1-resource players; 0-resource players excluded.
    4. Non-participants act: Craftsman auto-repairs if conditions are met; everyone else gathers.
    5. Complication — a complication card is drawn (Sailor gets best of two on boat missions).
    6. Resolution — mission is attempted; on success bonuses are applied; on failure a
       volcano card is drawn (eruption ends the game immediately).
    7. Exhaustion — participants are exhausted; Ash in the Air adds an extra round.
    8. Gather — gatherers draw resources; Heat Wave cancels gathering.
    9. Mission maintenance — completed mission is replaced from the pool.
   10. Active player index advances.

    Args:
        state: Current game state, mutated in place.

    Returns:
        A (game_over, won) tuple. game_over is True when the game ends (win or eruption loss).
    """
    state.round += 1
    update_tool_repairs(state)
    refresh_exhaustion(state)

    # Step 1 — Identify active player before any list mutations
    active_player = state.players[state.active_player_index]

    # Step 2 — Active player decision
    action = decide_active_player_action(active_player, state)

    if action == ActivePlayerAction.SHUFFLE_MISSIONS:
        _apply_shuffle_cost(active_player)
        random.shuffle(state.mission_pool)
        if _handle_volcano_draw(state):
            return True, False
        state.active_player_index = (state.active_player_index + 1) % len(state.players)
        return False, False

    # action == ActivePlayerAction.CHOOSE_MISSION
    mission_name = vote_for_mission(active_player, state)

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

        # Step 3 — Participant selection
        participants = select_participants(active_player, mission, state)
        non_participants = [player for player in state.players if player not in participants]

        # Step 4 — Non-participant actions (repair or gather)
        gatherers = _apply_non_participant_actions(state, non_participants)

        # Step 5 — Complication
        complication = _draw_complication_card(state, participants, mission)

        # Step 6 — Resolution
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

        # Step 7 — Exhaustion
        _apply_exhaustion_step(state, participants, no_exhaustion)

    # Step 8 — Gather
    _apply_gather_step(state, gatherers)

    # Step 9 — Mission maintenance
    if success:
        state.active_missions.remove(mission_name)
        new_mission = draw_mission(state)
        if new_mission:
            state.active_missions.append(new_mission)

    # Win check
    if len(state.boat_parts_built) >= state.boat_parts_required:
        return True, True

    # No mission lost check (boat mission discarded with no replacement)
    if not state.active_missions:
        return True, False

    # Step 10 — Advance active player
    state.active_player_index = (state.active_player_index + 1) % len(state.players)

    return False, False


def run_game(
    player_count:                 int,
    initial_resources_per_player: int  = 3,
    deck_resource_count:          int  = 20,
    urgent_volcano_threshold:     int  = 4,
    verbose:                      bool = False,
) -> GameRecord:
    """
    Run a single complete game and return a record of the outcome.

    The game runs for up to 200 rounds. If the round limit is reached without a win
    or eruption, the result is recorded as a loss.

    Args:
        player_count:                Number of players (6-8).
        initial_resources_per_player: Resources dealt to each player at game start.
        deck_resource_count:         Number of each resource type in the deck.
        urgent_volcano_threshold:    Volcano deck size at which agents prioritise boat missions.
        verbose:                     If True, print a round-by-round trace to stdout.

    Returns:
        A GameRecord with the outcome, scores, and game statistics.
    """
    state = init_game(
        player_count,
        initial_resources_per_player = initial_resources_per_player,
        deck_resource_count          = deck_resource_count,
        urgent_volcano_threshold     = urgent_volcano_threshold,
    )

    if verbose:
        print(f"Characters: {[p.character.value for p in state.players]}")
        print(f"Boat parts required: {state.boat_parts_required}")
        print(f"Active missions: {[m.value for m in state.active_missions]}")
        print()

    for _ in range(200):
        prev_volcano = len(state.volcano_deck)
        prev_missions = list(state.active_missions)
        prev_scores = [p.score for p in state.players]
        active_player = state.players[state.active_player_index]

        game_over, won = run_round(state)

        if verbose:
            completed_missions = [m for m in prev_missions if m not in state.active_missions]
            completed = completed_missions[0].value if completed_missions else "—"
            volcano_used = prev_volcano - len(state.volcano_deck)
            scores = [p.score for p in state.players]
            score_gains = [scores[i] - prev_scores[i] for i in range(len(scores))]
            print(
                f"Round {state.round:>2} | active: {active_player.character.value:<12} "
                f"| mission: {completed:<28} "
                f"| volcano left: {len(state.volcano_deck):>2} (used {volcano_used}) "
                f"| boat: {len(state.boat_parts_built)}/{state.boat_parts_required} "
                f"| scores: {scores} (+{score_gains})"
            )

        if game_over:
            outcome = "win" if won else "loss"
            break
    else:
        outcome = "loss"

    if verbose:
        print()
        print(f"Outcome: {'WIN' if outcome == 'win' else 'LOSS'} after {state.round} rounds")
        print(f"Final scores: { {p.character.value: p.score for p in state.players} }")
        print(f"Boat parts built: {len(state.boat_parts_built)}/{state.boat_parts_required}")
        print(f"Volcano cards remaining: {len(state.volcano_deck)}")
        print(f"Resources consumed: { {r.value: n for r, n in state.resources_consumed.items()} }")
        failures_by_resource = {r.value: n for r, n in state.mission_failures_by_resource.items()}
        failures_tool = {t.value: n for t, n in state.mission_failures_tool_damaged.items()}
        print(f"Mission failures by resource: {failures_by_resource}  (any_extra: {state.mission_failures_any_extra}, tool_damaged: {failures_tool})")
        print(f"Tool repairs: { {t.value: n for t, n in state.tool_repairs.items()} }")

    return GameRecord(
        player_count                  = player_count,
        characters                    = [p.character for p in state.players],
        outcome                       = outcome,
        rounds_played                 = state.round,
        final_scores                  = {p.character: p.score for p in state.players},
        boat_parts_built              = len(state.boat_parts_built),
        boat_parts_required           = state.boat_parts_required,
        volcano_cards_remaining       = len(state.volcano_deck),
        resources_consumed            = dict(state.resources_consumed),
        mission_failures_by_resource  = dict(state.mission_failures_by_resource),
        mission_failures_any_extra    = state.mission_failures_any_extra,
        mission_failures_tool_damaged = dict(state.mission_failures_tool_damaged),
        tool_repairs                  = dict(state.tool_repairs),
    )


def run_scenario(
    player_count:                 int,
    n_games:                      int,
    base_seed:                    Optional[int] = None,
    initial_resources_per_player: int           = 3,
    deck_resource_count:          int           = 20,
    urgent_volcano_threshold:     int           = 4,
) -> list[GameRecord]:
    """
    Run multiple games with the same player count and collect the results.

    Args:
        player_count:                Number of players per game (6-8).
        n_games:                     Number of games to simulate.
        base_seed:                   If provided, seeds each game deterministically (base_seed + game_index)
                                     for reproducible results.
        initial_resources_per_player: Resources dealt to each player at game start.
        deck_resource_count:         Number of each resource type in the deck.
        urgent_volcano_threshold:    Volcano deck size at which agents prioritise boat missions.

    Returns:
        List of GameRecord, one per game.
    """
    results = []
    for i in range(n_games):
        if base_seed is not None:
            random.seed(base_seed + i)

        results.append(run_game(
            player_count,
            initial_resources_per_player = initial_resources_per_player,
            deck_resource_count          = deck_resource_count,
            urgent_volcano_threshold     = urgent_volcano_threshold,
        ))

    return results
