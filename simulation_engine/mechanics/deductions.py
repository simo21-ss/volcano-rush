from collections import Counter

from ..models import GameState, Player, MissionRequirement


def deduct_costs(player_requirements: list[tuple[Player, MissionRequirement]], state: GameState) -> None:
    """
    Remove each participant's personal cost from their hand. Caller is responsible
    for confirming affordability first (see affordability.can_afford); this
    function assumes the check has passed.

    Args:
        player_requirements: Output of apply_character_discounts.
        state: Current game state (used for resources_consumed telemetry).
    """
    for player, personal in player_requirements:
        for resource, needed in personal.typed.items():
            for _ in range(needed):
                player.resources.remove(resource)
            state.resources_consumed[resource] = state.resources_consumed.get(resource, 0) + needed

        remaining_any = personal.any_extra
        if remaining_any > 0:
            resources_by_type = Counter(player.resources)
            for resource in sorted(resources_by_type, key = lambda r: -resources_by_type[r]):
                take = min(remaining_any, resources_by_type[resource])
                for _ in range(take):
                    player.resources.remove(resource)
                state.resources_consumed[resource] = state.resources_consumed.get(resource, 0) + take
                remaining_any -= take
                if remaining_any <= 0:
                    break
