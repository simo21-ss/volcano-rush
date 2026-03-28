import random
from typing import Optional
import numpy as np

from ..models import (
    Character, Resource, MissionType,
    GameState, Player, Mission, ComplicationCard, VolcanoCard,
    MissionRequirement, RESOURCE_INDEX,
)


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

    for player in participants:
        if player.character == Character.BUILDER:
            if resource_requirements.get(Resource.WOOD, 0) >= 2:
                resource_requirements[Resource.WOOD] = resource_requirements[Resource.WOOD] - 1
        elif player.character == Character.FIRE_STARTER:
            if mission.mission_type == MissionType.FIRE:
                any_extra -= 1

    # Clamp
    resource_requirements = {resource: max(0, value) for resource, value in resource_requirements.items()}
    any_extra = max(0, any_extra)

    return MissionRequirement(typed = resource_requirements, any_extra = any_extra)


def check_and_contribute(
    participants:  list[Player],
    requirements:  MissionRequirement,
    max_per_type:  Optional[int],
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
    # Build available pool as a resource-count array, respecting Camp Panic cap
    available = np.zeros(3, dtype = np.int32)
    for player in participants:
        if max_per_type is not None:
            available += np.minimum(player.resources, max_per_type)
        else:
            available += player.resources

    # Build required array from typed dict
    required = np.zeros(3, dtype = np.int32)
    for resource, amount in requirements.typed.items():
        required[RESOURCE_INDEX[resource]] = amount

    # Negative surplus means a typed requirement is unmet — return without deducting
    surplus = available - required
    if np.any(surplus < 0):
        return False

    # Total surplus must cover the wildcard any_extra requirement
    if int(surplus.sum()) < requirements.any_extra:
        return False

    # Deduct typed requirements, then fill any_extra greedily (prefer most-abundant surplus)
    to_remove = required.copy()
    remaining_any = requirements.any_extra
    for index in np.argsort(-surplus):
        take = min(remaining_any, int(surplus[index]))
        to_remove[index] += take
        remaining_any -= take
        if remaining_any <= 0:
            break

    # Remove from player hands in order
    for player in participants:
        deduct = np.minimum(player.resources, to_remove)
        player.resources -= deduct
        to_remove -= deduct

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

    # Tool availability
    for tool in mission.required_tools:
        if state.tools[tool].damaged:
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
    )

    if success and complication.damages_tool_on_success is not None:
        state.tools[complication.damages_tool_on_success].damaged = True

    return success
