import random
from typing import Optional

from ..models import (
    ActivePlayerAction, MissionType,
    GameState, Mission, VolcanoCard, GameOutcome,
)
from ..mechanics import refresh_exhaustion, update_tool_repairs, resolve_mission
from ..deck import draw_mission
from ..agents import (
    vote_for_mission, decide_active_player_action, active_player_select_participants,
)
from .phases import (
    handle_volcano_draw, handle_panic_cap_round,
    apply_non_participant_actions, apply_shuffle_cost,
    draw_complication_card, apply_mission_success,
    apply_exhaustion_step, apply_gather_step,
)


def run_round(state: GameState) -> Optional[GameOutcome]:
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
    3. Participant selection - active player's choice, preferring players with 2+
       resources over 1-resource players; 0-resource players excluded.
    4. Non-participants act: Craftsman auto-repairs if conditions are met; everyone else gathers.
    5. Complication - a complication card is drawn (Sailor gets best of two on boat missions).
    6. Resolution - mission is attempted; on success bonuses are applied; on failure a
       volcano card is drawn (eruption ends the game immediately).
    7. Exhaustion - participants are exhausted; Ash in the Air adds an extra round.
    8. Gather - gatherers draw resources; Heat Wave cancels gathering.
    9. Mission maintenance - completed mission is replaced from the pool.
   10. Active player index advances.

    Args:
        state: Current game state, mutated in place.

    Returns:
        The GameOutcome when the game ends this round (win or eruption loss), or None if the game continues.
    """
    state.round += 1
    update_tool_repairs(state)
    refresh_exhaustion(state)

    # Step 1 - Identify active player before any list mutations
    active_player = state.players[state.active_player_index]

    # Step 2 - Active player decision
    action = decide_active_player_action(active_player, state)

    if action == ActivePlayerAction.SHUFFLE_MISSIONS:
        apply_shuffle_cost(active_player)
        random.shuffle(state.mission_pool)

        if handle_volcano_draw(state):
            return GameOutcome.LOSS

        state.active_player_index = (state.active_player_index + 1) % len(state.players)
        return None

    # action == ActivePlayerAction.CHOOSE_MISSION
    mission_name = vote_for_mission(active_player, state)

    if mission_name is None:
        participants, gatherers, success, no_exhaustion, eruption = handle_panic_cap_round(state)
        if eruption:
            return GameOutcome.LOSS
    else:
        mission = Mission.get(mission_name)

        # Clear Panic if it was the pending card
        if (state.pending_volcano_card is not None
                and VolcanoCard.get(state.pending_volcano_card).max_mission_participants is not None):
            state.pending_volcano_card = None

        # Step 3 - Participant selection
        participants = active_player_select_participants(active_player, mission, state)
        non_participants = [player for player in state.players if player not in participants]

        # Step 4 - Non-participant actions (repair or gather)
        gatherers = apply_non_participant_actions(state, non_participants)

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
    apply_gather_step(state, gatherers)

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
    state.active_player_index = (state.active_player_index + 1) % len(state.players)

    return None
