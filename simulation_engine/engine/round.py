from typing import Optional

from .phases import (
    handle_volcano_draw,
    decide_non_participant_actions,
    draw_complication_card, apply_mission_success,
    apply_exhaustion_step, apply_gather_step,
)
from ..actions import PlayerAction, ShuffleMissionsAction, GatherAction, RepairAction
from ..agents import (
    decide_mission_action, vote_for_mission, active_player_select_participants,
    MissionSelector, ParticipantSelector,
)
from ..deck import draw_mission
from ..mechanics.mission import resolve_mission
from ..models import (
    MissionType, MissionName,
    Player, GameState, Mission, GameOutcome,
)


def run_round(
        state: GameState,
        mission_selector: Optional[MissionSelector] = None,
        participant_selector: Optional[ParticipantSelector] = None,
) -> Optional[GameOutcome]:
    """
    Execute one full round of the game.

    The active player either shuffles the mission pool or picks a mission.
    Shuffle rounds and Panic-forfeit rounds end with a volcano draw. Mission
    rounds pick participants, draw a complication, resolve the mission, then
    handle exhaustion, non-participant gather, and mission maintenance.

    Args:
        state: The current game state, mutated in place.
        mission_selector: Policy choosing which mission to attempt. When None,
            the rule-based vote_for_mission is used, preserving default behaviour.
        participant_selector: Policy choosing who joins the mission. When None,
            the rule-based active_player_select_participants is used.

    Returns the GameOutcome if the game ends this round, else None.
    """
    if mission_selector is None:
        mission_selector = vote_for_mission
    if participant_selector is None:
        participant_selector = active_player_select_participants

    active_player = state.begin_round()

    action = decide_mission_action(active_player, state)
    if action == PlayerAction.SHUFFLE_MISSIONS:
        return _run_shuffle_round(active_player, state)

    mission_name = mission_selector(active_player, state)
    if mission_name is None:
        return _run_forfeit_round(state)

    return _run_mission_round(active_player, mission_name, state, participant_selector)


def _run_shuffle_round(active_player: Player, state: GameState) -> Optional[GameOutcome]:
    ShuffleMissionsAction().execute(active_player, state)

    if handle_volcano_draw(state):
        return GameOutcome.LOSS

    return state.end_round()


def _run_forfeit_round(state: GameState) -> Optional[GameOutcome]:
    """
    Panic pending, all active missions are boats, no resources to shuffle:
    no legal mission, round forfeits.
    """
    if state.protect_next_failure:
        state.protect_next_failure = False
    elif handle_volcano_draw(state):
        return GameOutcome.LOSS

    return state.end_round()


def _run_mission_round(
        active_player: Player,
        mission_name: MissionName,
        state: GameState,
        participant_selector: ParticipantSelector,
) -> Optional[GameOutcome]:
    mission = Mission.get(mission_name)

    participants = participant_selector(active_player, mission, state)

    non_participants = [player for player in state.players if player not in participants]

    decisions = decide_non_participant_actions(state, non_participants)
    for player, action in decisions:
        if isinstance(action, RepairAction):
            action.execute(player, state)

    gather_actions = [(player, action) for player, action in decisions if isinstance(action, GatherAction)]

    complication = draw_complication_card(state, participants, mission) if participants else None
    success = resolve_mission(state, mission, participants, complication)

    if success:
        for player in participants:
            player.contribution.missions_participated += 1
            if mission.mission_type == MissionType.BOAT:
                player.contribution.boat_missions_participated += 1
        apply_mission_success(state, mission, mission_name, participants)
    else:
        if state.protect_next_failure:
            state.protect_next_failure = False
        else:
            if handle_volcano_draw(state):
                return GameOutcome.LOSS

    apply_exhaustion_step(state, participants)
    apply_gather_step(state, gather_actions)

    if success:
        state.active_missions.remove(mission_name)
        new_mission = draw_mission(state)
        if new_mission:
            state.active_missions.append(new_mission)

    return state.end_round()
