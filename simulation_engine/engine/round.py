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
)
from ..mechanics.mission import resolve_mission
from ..models import (
    MissionType, MissionName,
    Player, GameState, Mission, GameOutcome,
)


def run_round(state: GameState) -> Optional[GameOutcome]:
    """
    Execute one full round of the game.

    The active player either shuffles the mission pool or picks a mission.
    Shuffle rounds and Panic-forfeit rounds end with a volcano draw. Mission
    rounds pick participants, draw a complication, resolve the mission, then
    handle exhaustion, non-participant gather, and mission maintenance.

    Returns the GameOutcome if the game ends this round, else None.
    """
    active_player = state.begin_round()

    action = decide_mission_action(active_player, state)
    if action == PlayerAction.SHUFFLE_MISSIONS:
        return _run_shuffle_round(active_player, state)

    mission_name = vote_for_mission(active_player, state)
    if mission_name is None:
        return _run_forfeit_round(state)

    return _run_mission_round(active_player, mission_name, state)


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


def _run_mission_round(active_player: Player, mission_name: MissionName, state: GameState) -> Optional[GameOutcome]:
    mission = Mission.get(mission_name)

    participants = active_player_select_participants(active_player, mission, state)

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

    return state.end_round(completed_mission = mission_name if success else None)
