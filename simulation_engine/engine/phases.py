import random
from typing import Optional

from ..models import (
    MissionName,
    Player, GameState, Mission, VolcanoCard, ComplicationCard,
)
from ..actions import GatherAction, NonParticipantAction
from ..characters import get_strategy
from ..deck import draw_complication, draw_volcano
from ..mechanics import apply_exhaustion, apply_volcano_card, apply_mission_bonus


def handle_volcano_draw(state: GameState) -> bool:
    """
    Draw a volcano card and apply or negate its effect.

    If the drawn card is an eruption, returns True immediately (caller must end
    the game). If state.pending_bonus can negate the card, the bonus is consumed
    and the card has no effect. Otherwise, the card is applied via apply_volcano_card.

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


def decide_non_participant_actions(state: GameState, non_participants: list[Player]) -> list[tuple[Player, NonParticipantAction]]:
    """
    Ask each non-participant's strategy what they'll do this round. Pure -
    no side effects. Dispatch (execute REPAIRs now, defer GATHERs to the
    gather step) is the caller's job.
    """
    return [
        (player, get_strategy(player.character).choose_non_participant_action(player, state))
        for player in non_participants
    ]


def draw_complication_card(state: GameState, participants: list, mission: Mission) -> Optional[ComplicationCard]:
    """
    Draw the complication card for this round's mission attempt.

    Three cases apply in order:
    1. If skip_next_complication is set, return None (no complication this round)
       and clear the flag.
    2. If any participant's strategy offers more than one draw (Sailor on a boat
       mission draws two), draw that many distinct cards and keep the one with
       the lowest severity - the best outcome for players.
    3. Otherwise, draw one card normally.

    Args:
        state: Current game state, mutated in place (skip_next_complication flag).
        participants: Players committed to the mission this round.
        mission: The selected mission for this round.

    Returns:
        The ComplicationCard to use for mission resolution, or None if the round
        has no complication.
    """
    if state.skip_next_complication:
        state.skip_next_complication = False

        return None

    max_draws = max((get_strategy(player.character).complication_draw_count(mission) for player in participants))

    if max_draws > 1:
        for player in participants:
            if get_strategy(player.character).complication_draw_count(mission) > 1:
                player.contribution.lesser_evil_uses += 1

        drawn_names = random.sample(state.complication_deck, max_draws)

        return min(
            (ComplicationCard.get(name) for name in drawn_names),
            key = lambda card: card.severity,
        )

    return ComplicationCard.get(draw_complication(state))


def apply_mission_success(state: GameState, mission: Mission, mission_name: MissionName, participants: list) -> bool:
    """
    Apply scoring and bonus effects after a mission succeeds.

    Computes each participant's adjusted point total (base points plus Fire Starter
    bonus, Cook bonus, minus Smoke penalty), awards the points, clears the Smoke
    volcano card if it applied a penalty, and processes the mission's bonus_on_success.

    Args:
        state: Current game state, mutated in place.
        mission: The mission that was completed.
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

    if point_penalty > 0:
        state.pending_volcano_card = None

    points_per_player = max(0, base_points + bonus_points - point_penalty)

    for player in participants:
        player.score += points_per_player

    return apply_mission_bonus(mission.bonus_on_success, mission_name, state)


def apply_exhaustion_step(state: GameState, participants: list, no_exhaustion: bool) -> None:
    """
    Apply exhaustion to mission participants at the end of the mission phase.

    If a pending volcano card carries extra_exhaustion_rounds (Ash in the Air),
    those extra rounds are read and the card is consumed before calling
    apply_exhaustion. The step is skipped entirely when no_exhaustion is True.

    Args:
        state: Current game state, mutated in place.
        participants: Players who participated in the mission this round.
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


def apply_gather_step(state: GameState, gather_actions: list[tuple[Player, GatherAction]]) -> None:
    """
    Execute the bucketed gather actions.

    Checks for a Heat Wave pending volcano card (which zeroes all gathering) and
    then dispatches each GatherAction, which reads state.pending_bonus for the
    per-player gather bonus. Clears state.pending_bonus at the end.

    Args:
        state: Current game state, mutated in place.
        gather_actions: (player, GatherAction) pairs collected by
                        run_round after decide_non_participant_actions.
    """
    gather_yields_zero = (
        VolcanoCard.get(state.pending_volcano_card).gather_yields_zero
        if state.pending_volcano_card is not None
        else False
    )

    if gather_yields_zero:
        state.pending_volcano_card = None
    else:
        for player, action in gather_actions:
            action.execute(player, state)

    state.pending_bonus = None
