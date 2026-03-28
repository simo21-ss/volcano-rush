import random
from typing import Optional

from ..models import MissionType, MissionName, VolcanoCardName, GameState, BonusEffect, VolcanoCard, Mission
from ..deck import draw_mission


def apply_volcano_card(
    volcano_card_name: VolcanoCardName,
    state:             GameState,
) -> None:
    """
    Apply the immediate effect of a volcano card drawn after a mission failure.

    Cards with immediate effects (resource loss, exhaustion extension, mission discard)
    are resolved now. Cards with persistent effects are stored in state.pending_volcano_card
    and consumed at the appropriate step of the next round.

    Args:
        volcano_card_name: The name of the drawn volcano card.
        state:             Current game state, mutated in place.
    """
    card = VolcanoCard.get(volcano_card_name)

    if card.each_player_loses_resources > 0:
        for player in state.players:
            if card.rich_player_loses_threshold is None or len(player.resources) >= card.rich_player_loses_threshold:
                for _ in range(card.each_player_loses_resources):
                    if player.resources:
                        player.resources.remove(random.choice(player.resources))

    if card.extend_exhaustion_rounds > 0:
        for player in state.players:
            if player.exhausted_until > state.round:
                player.exhausted_until += card.extend_exhaustion_rounds

    if card.discard_mission:
        non_boat_missions = [m for m in state.active_missions if Mission.catalog[m].mission_type != MissionType.BOAT]
        candidates = non_boat_missions if non_boat_missions else list(state.active_missions)
        if candidates:
            discarded = random.choice(candidates)
            state.active_missions.remove(discarded)

            replacement = draw_mission(state)
            if replacement:
                state.active_missions.append(replacement)

    is_immediate = card.each_player_loses_resources > 0 or card.extend_exhaustion_rounds > 0 or card.discard_mission
    if not is_immediate:
        state.pending_volcano_card = volcano_card_name


def apply_bonus(
    bonus:        Optional[BonusEffect],
    participants: list,
    mission_name: MissionName,
    state:        GameState,
) -> bool:
    """
    Apply a mission success bonus effect to the game state.

    Handles all bonus types: boat part registration, complication skip, failure protection,
    tool repair, volcano card negation, and resource discounts / gather bonuses for next round.

    Args:
        bonus:        The bonus effect to apply, or None if the mission has no bonus.
        participants: Players who completed the mission (used if the bonus grants no exhaustion).
        mission_name: The completed mission's name (used to register a boat part if applicable).
        state:        Current game state, mutated in place.

    Returns:
        True if participants should skip exhaustion this round, False otherwise.
    """
    if bonus is None:
        return False

    if bonus.boat_part:
        state.boat_parts_built.add(mission_name)

    if bonus.skip_next_complication:
        state.skip_next_complication = True

    if bonus.protect_next_failure:
        state.protect_next_failure = True

    if bonus.repair_tool:
        for tool, tool_state in state.tools.items():
            if tool_state.damaged:
                tool_state.damaged = False
                tool_state.repair_due = None
                break

    if bonus.negates_volcano_card is not None:
        if state.pending_volcano_card == bonus.negates_volcano_card:
            state.pending_volcano_card = None

    if bonus.resource_discount or bonus.resource_discount_any > 0 or bonus.gather_bonus > 0:
        state.pending_bonus = bonus

    return bonus.no_exhaustion
