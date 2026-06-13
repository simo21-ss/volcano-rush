import random
from typing import Optional

from .round import run_round
from ..agents import MissionSelector, ParticipantSelector
from ..initialization import init_game
from ..models import GameRecord, GameState, GameOutcome, MissionName, Player


def run_game(
        player_count: int,
        initial_resources_per_player: int = 3,
        deck_resource_count: int = 20,
        urgent_volcano_threshold: int = 4,
        verbose: bool = False,
        mission_selector: Optional[MissionSelector] = None,
        participant_selector: Optional[ParticipantSelector] = None,
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
        mission_selector:            Policy choosing which mission to attempt. When None,
                                     the rule-based vote_for_mission is used (default behaviour).
        participant_selector:        Policy choosing who joins the mission. When None,
                                     the rule-based active_player_select_participants is used.

    Returns:
        A GameRecord with the outcome, scores, and game statistics.
    """
    state = init_game(player_count, initial_resources_per_player, deck_resource_count, urgent_volcano_threshold)

    if verbose:
        _print_verbose_game_init(state)

    for _ in range(200):
        prev_volcano = len(state.volcano_deck)
        prev_missions = list(state.active_missions)
        prev_scores = [p.score for p in state.players]
        active_player = state.players[state.active_player_index]

        outcome = run_round(state, mission_selector, participant_selector)

        if verbose:
            _print_verbose_round_results(active_player, prev_missions, prev_scores, prev_volcano, state)

        if outcome is not None:
            break
    else:
        outcome = GameOutcome.LOSS

    if verbose:
        _print_verbose_game_results(outcome, state)

    contributions = { p.character: p.contribution for p in state.players } if outcome == GameOutcome.WIN else { }

    return GameRecord(
        player_count = player_count,
        characters = [p.character for p in state.players],
        outcome = outcome,
        rounds_played = state.round,
        final_scores = { p.character: p.score for p in state.players },
        boat_parts_built = len(state.boat_parts_built),
        boat_parts_required = state.boat_parts_required,
        volcano_cards_remaining = len(state.volcano_deck),
        resources_consumed = dict(state.resources_consumed),
        mission_failures_by_resource = dict(state.mission_failures_by_resource),
        mission_failures_any_extra = state.mission_failures_any_extra,
        mission_failures_tool_damaged = dict(state.mission_failures_tool_damaged),
        tool_repairs = dict(state.tool_repairs),
        contributions = contributions,
    )


def run_scenario(
        player_count: int,
        n_games: int,
        base_seed: Optional[int] = None,
        initial_resources_per_player: int = 3,
        deck_resource_count: int = 20,
        urgent_volcano_threshold: int = 4,
        mission_selector: Optional[MissionSelector] = None,
        participant_selector: Optional[ParticipantSelector] = None,
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
        mission_selector:            Policy choosing which mission to attempt. When None,
                                     the rule-based vote_for_mission is used (default behaviour).
        participant_selector:        Policy choosing who joins the mission. When None,
                                     the rule-based active_player_select_participants is used.

    Returns:
        List of GameRecord, one per game.
    """
    results = []
    for i in range(n_games):
        if base_seed is not None:
            random.seed(base_seed + i)

        game_result = run_game(
            player_count,
            initial_resources_per_player,
            deck_resource_count,
            urgent_volcano_threshold,
            mission_selector = mission_selector,
            participant_selector = participant_selector,
        )
        results.append(game_result)

    return results


def _print_verbose_game_init(state: GameState) -> None:
    print(f"Characters: {[p.character.value for p in state.players]}")
    print(f"Boat parts required: {state.boat_parts_required}")
    print(f"Active missions: {[m.value for m in state.active_missions]}")
    print()


def _print_verbose_round_results(
        active_player: Player,
        prev_missions: list[MissionName], prev_scores: list[int],
        prev_volcano: int,
        state: GameState
) -> None:
    completed_missions = [m for m in prev_missions if m not in state.active_missions]
    completed = completed_missions[0].value if completed_missions else "-"
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


def _print_verbose_game_results(outcome: GameOutcome, state: GameState) -> None:
    failures_by_resource = { r.value: n for r, n in state.mission_failures_by_resource.items() }
    failures_tool = { t.value: n for t, n in state.mission_failures_tool_damaged.items() }

    print()
    print(f"Outcome: {'WIN' if outcome == GameOutcome.WIN else 'LOSS'} after {state.round} rounds")
    print(f"Final scores: { { p.character.value: p.score for p in state.players } }")
    print(f"Boat parts built: {len(state.boat_parts_built)}/{state.boat_parts_required}")
    print(f"Volcano cards remaining: {len(state.volcano_deck)}")
    print(f"Resources consumed: { { r.value: n for r, n in state.resources_consumed.items() } }")
    print(f"Mission failures by resource: {failures_by_resource}  (any_extra: {state.mission_failures_any_extra}, tool_damaged: {failures_tool})")
    print(f"Tool repairs: { { t.value: n for t, n in state.tool_repairs.items() } }")
