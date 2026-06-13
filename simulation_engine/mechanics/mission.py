from typing import Optional

from ..models import (
    GameState, Player, Mission, ComplicationCard, VolcanoCard, MissionRequirement,
)
from .requirements import (
    compute_per_player_requirements, compute_complication_extras, compute_volcano_extras,
)
from .affordability import apply_character_discounts, can_afford
from .deductions import deduct_costs


def resolve_mission(
        state: GameState,
        mission: Mission,
        participants: list[Player],
        complication: Optional[ComplicationCard],
) -> bool:
    """
    Attempt to resolve a mission with the given participants and complication card.

    Every resource cost - base mission, complication extras, and volcano card
    extras - is charged to each participant individually. `complication` may be
    None when the round has no complication (e.g. skip_next_complication was set).

    Args:
        state: Current game state (tools, players, pending effects).
        mission: The mission being attempted.
        participants: Players contributing resources to the mission.
        complication: The complication card drawn for this attempt, or None.

    Returns:
        True if the mission succeeds and resources are deducted, False otherwise.
    """
    if not _preconditions_met(mission, participants, complication, state):
        return False

    cost_paying = list(participants)
    if complication is not None and complication.requires_extra_helper:
        helper = _find_night_anxiety_helper(state, participants)
        if helper is None:
            return False
        cost_paying.append(helper)

    per_player = _build_per_player_requirement(mission, complication, state)
    max_per_type = complication.max_resource_per_type if complication is not None else None

    player_requirements = apply_character_discounts(cost_paying, per_player, mission)
    success = can_afford(player_requirements, max_per_type, state)
    if success:
        deduct_costs(player_requirements, state)

    _consume_volcano_extras_card(state)

    if success and complication is not None and complication.damages_tool_on_success is not None:
        state.tools[complication.damages_tool_on_success].damaged = True

    return success


def _preconditions_met(
        mission: Mission,
        participants: list[Player],
        complication: Optional[ComplicationCard],
        state: GameState,
) -> bool:
    if len(participants) != mission.players_count:
        return False

    for tool in mission.required_tools:
        if state.tools[tool].damaged:
            state.mission_failures_tool_damaged[tool] = (
                    state.mission_failures_tool_damaged.get(tool, 0) + 1
            )
            return False

    return True


def _find_night_anxiety_helper(state: GameState, participants: list[Player]) -> Optional[Player]:
    """
    Pick the first non-participant, non-exhausted player to stand in as a Night
    Anxiety helper. The helper will be charged the same per-participant cost as
    a regular participant. If no eligible helper exists, returns None and the
    caller fails the mission.
    """
    return next(
        (player for player in state.players if player not in participants and not player.is_exhausted),
        None,
    )


def _build_per_player_requirement(
        mission: Mission,
        complication: Optional[ComplicationCard],
        state: GameState,
) -> MissionRequirement:
    base = compute_per_player_requirements(mission, state)
    complication_extras = compute_complication_extras(mission, complication)
    volcano_extras = compute_volcano_extras(mission, state)
    return _combine_requirements([base, complication_extras, volcano_extras])


def _combine_requirements(requirements: list[MissionRequirement]) -> MissionRequirement:
    typed: dict = {}
    any_extra = 0
    for requirement in requirements:
        for resource, amount in requirement.typed.items():
            typed[resource] = typed.get(resource, 0) + amount
        any_extra += requirement.any_extra
    return MissionRequirement(typed = typed, any_extra = any_extra)


def _consume_volcano_extras_card(state: GameState) -> None:
    """
    Drop any pending cards whose resource extras have been applied to this
    mission attempt (RAIN_AND_MUD, LAVA_FLOW). Non-extras pending cards
    (SMOKE, ASH_IN_THE_AIR, PANIC) are consumed by their own phase handlers.
    """
    state.pending_volcano_cards = [
        card_name for card_name in state.pending_volcano_cards
        if not VolcanoCard.get(card_name).extra_resources
    ]
