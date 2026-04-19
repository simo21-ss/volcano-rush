from collections import Counter
from enum import Enum

from ..models import Player, GameState, Mission, MissionRequirement
from ..characters import get_strategy
from ..mechanics.requirements import compute_per_player_requirements


class AffordLevel(Enum):
    EXACT = "exact"
    SURPLUS = "surplus"
    CANNOT_AFFORD = "cannot_afford"


def player_afford_level(player: Player, mission: Mission, state: GameState) -> AffordLevel:
    """
    Classify how well the player can pay the mission's per-player cost.

    Character discount and any pending typed bonus discount are both reflected.
    Complication extras are not visible yet at feasibility time (complications
    are drawn after mission selection), so this is a best-case classification
    against the base per-player cost.

    Returns:
        EXACT - hand exactly covers the personal cost, no surplus
        SURPLUS - hand covers the personal cost with resources left over
        CANNOT_AFFORD - hand cannot cover the personal cost
    """
    base = compute_per_player_requirements(mission, state)
    personal = _personal_requirement(player, mission, base)

    resources_by_type = Counter(player.resources)
    meets_typed = all(
        resources_by_type.get(resource, 0) >= needed
        for resource, needed in personal.typed.items()
    )
    if not meets_typed:
        return AffordLevel.CANNOT_AFFORD

    total_surplus = sum(resources_by_type.values()) - sum(personal.typed.values())
    if total_surplus < personal.any_extra:
        return AffordLevel.CANNOT_AFFORD

    return AffordLevel.EXACT if total_surplus == personal.any_extra else AffordLevel.SURPLUS


def team_can_afford(mission: Mission, state: GameState) -> bool:
    """
    Check whether the team could successfully staff the mission right now.

    Counts non-exhausted players whose hand individually satisfies the per-player
    requirement after applying their own character's discount, then checks that
    the count is at least the mission's required participants. Also fails if any
    required tool is currently damaged.

    Args:
        mission: The mission being evaluated.
        state:   Current game state (players, tools, pending bonus).

    Returns:
        True if the team has enough affordable, available participants; False otherwise.
    """
    for tool in mission.required_tools:
        if state.tools[tool].damaged:
            return False

    affordable_count = 0
    for player in state.players:
        if player.is_exhausted:
            continue
        if player_afford_level(player, mission, state) != AffordLevel.CANNOT_AFFORD:
            affordable_count += 1
            if affordable_count >= mission.players_count:
                return True

    return False


def _personal_requirement(player: Player, mission: Mission, base_requirement: MissionRequirement) -> MissionRequirement:
    personal = get_strategy(player.character).requirement_discount(mission, base_requirement)
    return MissionRequirement(
        typed = { resource: max(0, value) for resource, value in personal.typed.items() },
        any_extra = max(0, personal.any_extra),
    )
