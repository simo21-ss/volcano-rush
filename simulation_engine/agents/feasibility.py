from collections import Counter

from ..models import Player, GameState, Mission, MissionRequirement
from ..characters import get_strategy
from ..mechanics.mission import compute_per_player_requirements


def personal_requirement(
    player:           Player,
    mission:          Mission,
    base_requirement: MissionRequirement,
) -> MissionRequirement:
    personal = get_strategy(player.character).requirement_discount(mission, base_requirement)
    return MissionRequirement(
        typed     = {resource: max(0, value) for resource, value in personal.typed.items()},
        any_extra = max(0, personal.any_extra),
    )


def player_afford_level(
    player:           Player,
    mission:          Mission,
    base_requirement: MissionRequirement,
) -> str:
    """
    Classify how well the player can pay for the mission.

    Returns one of:
        "exact"   - hand fully covers cost with no resources left over
        "surplus" - hand fully covers cost with spare resources remaining
        "partial" - hand cannot fully cover cost but has at least one resource
        "empty"   - player has no resources
    """
    if not player.resources:
        return "empty"

    personal = personal_requirement(player, mission, base_requirement)
    resources_by_type = Counter(player.resources)

    meets_typed = all(
        resources_by_type.get(resource, 0) >= needed
        for resource, needed in personal.typed.items()
    )
    if not meets_typed:
        return "partial"

    surplus = sum(
        resources_by_type.get(resource, 0) - personal.typed.get(resource, 0)
        for resource in set(resources_by_type) | set(personal.typed)
    )
    if surplus < personal.any_extra:
        return "partial"

    return "exact" if surplus - personal.any_extra == 0 else "surplus"


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

    base_requirement = compute_per_player_requirements(mission, state)

    affordable_count = 0
    for player in state.players:
        if player.is_exhausted:
            continue
        if player_afford_level(player, mission, base_requirement) in ("exact", "surplus"):
            affordable_count += 1
            if affordable_count >= mission.players_count:
                return True

    return False
