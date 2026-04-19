from collections import Counter
from typing import Optional

from ..characters import get_strategy
from ..models import GameState, Player, Mission, MissionRequirement


def apply_character_discounts(
        participants: list[Player],
        per_player_requirements: MissionRequirement,
        mission: Mission,
) -> list[tuple[Player, MissionRequirement]]:
    """
    Apply each participant's character discount to the per-player requirement.

    Bumps each player's requirement_discounts_used counter when the discount
    actually changes the cost.

    Args:
        participants: Players attempting the mission.
        per_player_requirements: Combined per-player base + complication cost.
        mission: The mission (needed by character strategies for conditional discounts).

    Returns:
        List of (player, personal_requirement) tuples, clamped to non-negative values.
    """
    player_requirements: list[tuple[Player, MissionRequirement]] = []
    for player in participants:
        strategy = get_strategy(player.character)
        typed_before = dict(per_player_requirements.typed)
        any_extra_before = per_player_requirements.any_extra
        personal = strategy.requirement_discount(mission, per_player_requirements)
        if personal.typed != typed_before or personal.any_extra != any_extra_before:
            player.contribution.requirement_discounts_used += 1
        personal = MissionRequirement(
            typed = { resource: max(0, value) for resource, value in personal.typed.items() },
            any_extra = max(0, personal.any_extra),
        )
        player_requirements.append((player, personal))
    return player_requirements


def can_afford(player_requirements: list[tuple[Player, MissionRequirement]], max_per_type: Optional[int], state: GameState) -> bool:
    """
    Check whether each participant can individually meet their personal requirement.

    Records failure reasons on state.mission_failures_* but never mutates
    player.resources.

    Args:
        player_requirements: Output of apply_character_discounts.
        max_per_type: Camp Panic cap on resources of the same type per player.
        state: Current game state (used only for failure telemetry).

    Returns:
        True if every participant can cover their personal requirement, False otherwise.
    """
    for player, personal in player_requirements:
        resources_by_type = _effective_resources(player, max_per_type)

        for resource, needed in personal.typed.items():
            if needed > 0 and resources_by_type.get(resource, 0) < needed:
                state.mission_failures_by_resource[resource] = (
                        state.mission_failures_by_resource.get(resource, 0) + 1
                )
                return False

        total_surplus = sum(
            resources_by_type.get(resource, 0) - personal.typed.get(resource, 0)
            for resource in set(resources_by_type) | set(personal.typed)
        )
        if total_surplus < personal.any_extra:
            state.mission_failures_any_extra += 1
            return False

    return True


def _effective_resources(player: Player, max_per_type: Optional[int]) -> Counter:
    resources_by_type = Counter(player.resources)
    if max_per_type is None:
        return resources_by_type

    return Counter({ resource: min(count, max_per_type) for resource, count in resources_by_type.items() })
