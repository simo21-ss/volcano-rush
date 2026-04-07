import random
from collections import Counter
from typing import Optional

from ..models import (
    Resource,
    GameState, Player, Mission, ComplicationCard, VolcanoCard,
    MissionRequirement,
)
from ..characters import get_strategy


def compute_requirements(
    mission:      Mission,
    participants: list[Player],
    complication: ComplicationCard,
    state:        GameState,
) -> MissionRequirement:
    """
    Compute the total mission requirements for a mission attempt.

    Applies all active modifiers in order:
    1. Base mission requirements
    2. Pending volcano card extra resources
    3. Complication card extra resources and per-participant surcharges
    4. Pending bonus discounts and character ability discounts

    Mission requirements are clamped to zero — discounts cannot go negative.

    Args:
        mission:      The mission being attempted.
        participants: Players participating in the mission.
        complication: The complication card drawn for this attempt.
        state:        Current game state (pending bonus, pending volcano card, etc.).

    Returns:
        Mission requirements with typed resource costs and a wildcard any_extra count.
        typed resources must be paid with the exact resource type;
        any_extra may be paid with any resource type.
    """
    resource_requirements = dict(mission.required_resources)
    any_extra = 0

    # Apply pending volcano card extra resources
    if state.pending_volcano_card is not None:
        volcano_card = VolcanoCard.get(state.pending_volcano_card)
        for resource, amount in volcano_card.extra_resources.items():
            if volcano_card.conditional_on_resource is None or volcano_card.conditional_on_resource in resource_requirements:
                resource_requirements[resource] = resource_requirements.get(resource, 0) + amount

    # Apply complication card extras
    for resource, amount in complication.extra_resources.items():
        if complication.conditional_on_resource is None or complication.conditional_on_resource in resource_requirements:
            resource_requirements[resource] = resource_requirements.get(resource, 0) + amount
    any_extra += complication.extra_resources_any
    any_extra += complication.extra_per_participant * len(participants)

    # Apply pending bonus discounts and character ability discounts
    if state.pending_bonus is not None:
        bonus = state.pending_bonus
        for resource, amount in bonus.resource_discount.items():
            resource_requirements[resource] = resource_requirements.get(resource, 0) - amount
        any_extra -= bonus.resource_discount_any

    requirements = MissionRequirement(typed = resource_requirements, any_extra = any_extra)
    for player in participants:
        strategy = get_strategy(player.character)
        requirements = strategy.requirement_discount(mission, requirements)

    # Clamp
    return MissionRequirement(
        typed     = {resource: max(0, value) for resource, value in requirements.typed.items()},
        any_extra = max(0, requirements.any_extra),
    )


def check_and_contribute(
    participants:  list[Player],
    requirements:  MissionRequirement,
    max_per_type:  Optional[int],
    state:         GameState,
) -> bool:
    """
    Check if participants can meet the typed and any_extra resource requirements,
    respecting max_per_type limits, and if so, deduct the resources from their hands.

    Args:
        participants: Players attempting the mission.
        requirements: Mission requirements with typed resource costs and a wildcard any_extra count.
        max_per_type: If set, limits the number of resources of the same type that can be
                      contributed per player (e.g. Camp Panic cap).

    Returns:
        True if requirements can be met and resources were deducted,
        False otherwise (no deduction on failure).
    """
    # Build available pool per resource (respecting Camp Panic cap)
    available: dict[Resource, int] = {}
    for player in participants:
        resources_by_type = Counter(player.resources)
        for resource, count in resources_by_type.items():
            if max_per_type is not None:
                count = min(count, max_per_type)
            available[resource] = available.get(resource, 0) + count

    # Net surplus per resource after subtracting typed requirements.
    # Union of both key sets ensures required-but-absent resources yield a negative entry.
    surplus_by_resource = {
        resource: available.get(resource, 0) - requirements.typed.get(resource, 0)
        for resource in set(available) | set(requirements.typed)
    }

    # Negative surplus means a typed requirement is unmet — return without deducting
    if any(surplus < 0 for surplus in surplus_by_resource.values()):
        for resource, surplus in surplus_by_resource.items():
            if surplus < 0:
                state.mission_failures_by_resource[resource] = (
                    state.mission_failures_by_resource.get(resource, 0) + 1
                )
        return False

    # Total surplus must cover the wildcard any_extra requirement
    if sum(surplus_by_resource.values()) < requirements.any_extra:
        state.mission_failures_any_extra += 1
        return False

    # Deduct typed requirements, then fill any_extra greedily (prefer most-abundant surplus)
    to_remove: dict[Resource, int] = dict(requirements.typed)
    remaining_any = requirements.any_extra
    for resource in sorted(surplus_by_resource, key = lambda r: -surplus_by_resource[r]):
        take = min(remaining_any, surplus_by_resource[resource])
        to_remove[resource] = to_remove.get(resource, 0) + take
        remaining_any -= take
        if remaining_any <= 0:
            break

    # Remove from player hands, ensuring each participant pays at least 1 resource.
    # Take from players with fewer resources first — they are constrained to specific
    # types, while players with more resources have flexibility to pay different types.
    participants_by_resources = sorted(participants, key = lambda player: len(player.resources))

    paid_players: set[int] = set()
    for resource, total in to_remove.items():
        left = total
        for player in participants_by_resources:
            while left > 0 and resource in player.resources:
                player.resources.remove(resource)
                paid_players.add(id(player))
                left -= 1

    for resource, amount in to_remove.items():
        state.resources_consumed[resource] = state.resources_consumed.get(resource, 0) + amount

    # Each participant must pay at least 1 resource (participation cost).
    # Players not yet charged pay 1 resource of any type.
    for player in participants_by_resources:
        if id(player) not in paid_players:
            resource = player.resources.pop(0)
            state.resources_consumed[resource] = state.resources_consumed.get(resource, 0) + 1

    return True


def resolve_mission(
    state:        GameState,
    mission:      Mission,
    participants: list[Player],
    complication: ComplicationCard,
) -> bool:
    """
    Attempt to resolve a mission with the given participants and complication card.

    Checks all preconditions (participant count, tool availability, complication helper
    requirement), computes the final resource requirements, and deducts resources on success.

    Args:
        state:        Current game state (tools, players, pending effects).
        mission:      The mission being attempted.
        participants: Players contributing resources to the mission.
        complication: The complication card drawn for this attempt.

    Returns:
        True if the mission succeeds and resources are deducted, False otherwise.
    """
    # Exact participant count
    if len(participants) != mission.players_count:
        return False

    # Every participant must hold at least 1 resource
    if any(len(player.resources) == 0 for player in participants):
        return False

    # Tool availability
    for tool in mission.required_tools:
        if state.tools[tool].damaged:
            state.mission_failures_tool_damaged[tool] = (
                state.mission_failures_tool_damaged.get(tool, 0) + 1
            )
            return False

    # Night Anxiety: need 1 non-participant, non-exhausted helper
    if complication.requires_extra_helper:
        helpers = [p for p in state.players if p not in participants and not p.is_exhausted]
        if not helpers:
            return False

    requirements = compute_requirements(mission, participants, complication, state)

    success = check_and_contribute(
        participants = participants,
        requirements = requirements,
        max_per_type = complication.max_resource_per_type,
        state        = state,
    )

    if success and complication.damages_tool_on_success is not None:
        state.tools[complication.damages_tool_on_success].damaged = True

    return success
