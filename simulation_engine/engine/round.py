from typing import Optional

from ..models import (
    MissionType, VolcanoCardName,
    GameState, Mission, GameOutcome,
)
from ..actions import PlayerAction, ShuffleMissionsAction
from ..mechanics import refresh_exhaustion, update_tool_repairs
from ..mechanics.mission import resolve_mission
from ..deck import draw_mission
from ..agents import (
    decide_mission_action, vote_for_mission, active_player_select_participants,
)
from .phases import (
    handle_volcano_draw,
    apply_non_participant_actions,
    draw_complication_card, apply_mission_success,
    apply_exhaustion_step, apply_gather_step,
)


def run_round(state: GameState) -> Optional[GameOutcome]:
    """
    Execute one full round of the game.

    Steps in order:
     1. Identify the active player.
     2. Active player decides: shuffle the mission deck or choose a mission.
     3. Participant selection.
     4. Non-participants act (gather or repair).
     5. Complication.
     6. Mission resolution.
     7. Exhaustion.
     8. Gather.
     9. Mission maintenance.
    10. Advance active player.

    Returns the GameOutcome if the game ends this round, else None.
    """
    state.round += 1
    update_tool_repairs(state)
    refresh_exhaustion(state)

    # Step 1 - Identify active player before any list mutations
    active_player = state.players[state.active_player_index]

    # Step 2 - Active player decision
    action = decide_mission_action(active_player, state)

    if action == PlayerAction.SHUFFLE_MISSIONS:
        ShuffleMissionsAction().execute(active_player, state)

        if handle_volcano_draw(state):
            return GameOutcome.LOSS

        state.advance_active_player()
        return None

    mission_name = vote_for_mission(active_player, state)

    if mission_name is None:
        # Panic pending, all active missions are boats, no resources to shuffle:
        # no legal mission, round forfeits.
        state.pending_volcano_card = None
        if state.protect_next_failure:
            state.protect_next_failure = False
        elif handle_volcano_draw(state):
            return GameOutcome.LOSS
        state.advance_active_player()
        return None

    mission = Mission.get(mission_name)

    # Clear pending Panic card (we chose a non-boat under the ban)
    if state.pending_volcano_card == VolcanoCardName.PANIC:
        state.pending_volcano_card = None

    # Step 3 - Participant selection
    participants = active_player_select_participants(active_player, mission, state)
    non_participants = [player for player in state.players if player not in participants]

    # Step 4 - Non-participant actions (repair or gather)
    gather_actions = apply_non_participant_actions(state, non_participants)

    # Step 5 - Complication
    complication = draw_complication_card(state, participants, mission)

    # Step 6 - Resolution
    success = resolve_mission(state, mission, participants, complication)

    if success:
        for player in participants:
            player.contribution.missions_participated += 1
            if mission.mission_type == MissionType.BOAT:
                player.contribution.boat_missions_participated += 1
        no_exhaustion = apply_mission_success(state, mission, mission_name, participants)
    else:
        no_exhaustion = False
        if state.protect_next_failure:
            state.protect_next_failure = False
        else:
            if handle_volcano_draw(state):
                return GameOutcome.LOSS

    # Step 7 - Exhaustion
    apply_exhaustion_step(state, participants, no_exhaustion)

    # Step 8 - Gather
    apply_gather_step(state, gather_actions)

    # Step 9 - Mission maintenance
    if success:
        state.active_missions.remove(mission_name)
        new_mission = draw_mission(state)
        if new_mission:
            state.active_missions.append(new_mission)

    # Win check
    if len(state.boat_parts_built) >= state.boat_parts_required:
        return GameOutcome.WIN

    # No mission lost check (boat mission discarded with no replacement)
    if not state.active_missions:
        return GameOutcome.LOSS

    # Step 10 - Advance active player
    state.advance_active_player()

    return None
