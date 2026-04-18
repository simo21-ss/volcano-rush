from collections import Counter
from typing import Optional

from ..characters import get_strategy
from ..models import (
    GameState, Player, Mission, ComplicationCard, VolcanoCard,
    MissionRequirement,
)


def compute_per_player_requirements(mission: Mission, state: GameState) -> MissionRequirement:
    """
    Compute the base per-player mission requirements.

    Applies only mission base cost and pending bonus discounts.
    Character ability discounts are applied per-player in check_and_contribute().

    Args:
        mission: The mission being attempted.
        state: Current game state (pending bonus, etc.).

    Returns:
        Per-player base requirements. Each participant must individually meet these.
    """
    resource_requirements = dict(mission.required_resources)
    any_extra = 0

    # Apply and consume any pending discount bonus from a previous mission success
    if state.pending_bonus is not None:
        bonus = state.pending_bonus
        if bonus.resource_discount or bonus.resource_discount_any > 0:
            for resource, amount in bonus.resource_discount.items():
                resource_requirements[resource] = resource_requirements.get(resource, 0) - amount
            any_extra -= bonus.resource_discount_any
            state.pending_bonus = None

    # Clamp
    return MissionRequirement(
        typed = { resource: max(0, value) for resource, value in resource_requirements.items() },
        any_extra = max(0, any_extra),
    )


def compute_group_extras(
        mission: Mission,
        complication: Optional[ComplicationCard],
        participants: list[Player],
        state: GameState,
) -> MissionRequirement:
    """
    Compute the one-time group extras from complication and volcano cards.

    These extras are paid once by the group as a whole from pooled surplus resources,
    not by every player individually.

    Args:
        mission: The mission being attempted.
        complication: The complication card drawn for this attempt, or None if
                      no complication was drawn (e.g. skip_next_complication).
        participants: Players participating (needed for extra_per_participant).
        state: Current game state (pending volcano card, etc.).

    Returns:
        One-time group extras with typed resource costs and a wildcard any_extra count.
    """
    resource_requirements: dict = { }
    any_extra = 0

    # Apply pending volcano card extra resources
    base_resources = mission.required_resources
    if state.pending_volcano_card is not None:
        volcano_card = VolcanoCard.get(state.pending_volcano_card)
        for resource, amount in volcano_card.extra_resources.items():
            if volcano_card.conditional_on_resource is None or volcano_card.conditional_on_resource in base_resources:
                resource_requirements[resource] = resource_requirements.get(resource, 0) + amount

    # Apply complication card extras (no-op when no complication was drawn)
    if complication is not None:
        for resource, amount in complication.extra_resources.items():
            if complication.conditional_on_resource is None or complication.conditional_on_resource in base_resources:
                resource_requirements[resource] = resource_requirements.get(resource, 0) + amount
        any_extra += complication.extra_resources_any
        any_extra += complication.extra_per_participant * len(participants)

    return MissionRequirement(typed = resource_requirements, any_extra = any_extra)


def check_and_contribute(
        participants: list[Player],
        per_player_requirements: MissionRequirement,
        group_extras: MissionRequirement,
        max_per_type: Optional[int],
        state: GameState,
        mission: Mission,
) -> bool:
    """
    Check if each participant individually meets the per-player requirements and the group
    can collectively cover the one-time extras, then deduct resources.

    Phase 1: Apply character discounts and check each player against per-player requirements.
    Phase 2: Check if the group's pooled surplus can cover the one-time group extras.
    Phase 3: Deduct per-player costs, then deduct group extras from the surplus.

    Args:
        participants: Players attempting the mission.
        per_player_requirements: Base per-player requirements (before character discounts).
        group_extras: One-time group extras from complications/volcano.
        max_per_type: If set, limits resources of the same type per player (Camp Panic).
        state: Current game state for tracking consumption and failures.
        mission: The mission being attempted (needed for character discount logic).

    Returns:
        True if all requirements are met and resources were deducted,
        False otherwise (no deduction on failure).
    """
    # Phase 1: Compute per-player requirements with individual character discounts
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

    # Phase 2a: Check each player individually against per-player requirements
    for player, personal in player_requirements:
        resources_by_type = Counter(player.resources)
        if max_per_type is not None:
            resources_by_type = Counter({ resource: min(count, max_per_type) for resource, count in resources_by_type.items() })

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

    # Phase 2b: Check group extras from pooled surplus after per-player costs
    if group_extras.typed or group_extras.any_extra > 0:
        pooled_surplus: Counter = Counter()
        for player, personal in player_requirements:
            resources_by_type = Counter(player.resources)
            if max_per_type is not None:
                resources_by_type = Counter({ resource: min(count, max_per_type) for resource, count in resources_by_type.items() })
            for resource in set(resources_by_type) | set(personal.typed):
                surplus = resources_by_type.get(resource, 0) - personal.typed.get(resource, 0) - personal.any_extra
                if surplus > 0:
                    pooled_surplus[resource] += surplus
            # Subtract any_extra that will consume from surplus (approximate - prefer most abundant)
            remaining_any = personal.any_extra
            for resource in sorted(resources_by_type, key = lambda r: -resources_by_type[r]):
                available = resources_by_type.get(resource, 0) - personal.typed.get(resource, 0)
                if available > 0 and remaining_any > 0:
                    take = min(remaining_any, available)
                    remaining_any -= take

        # Check typed group extras
        for resource, needed in group_extras.typed.items():
            if needed > 0 and pooled_surplus.get(resource, 0) < needed:
                state.mission_failures_by_resource[resource] = (
                        state.mission_failures_by_resource.get(resource, 0) + 1
                )
                return False
            pooled_surplus[resource] -= needed

        # Check any_extra group extras
        total_pool = sum(max(0, v) for v in pooled_surplus.values())
        if total_pool < group_extras.any_extra:
            state.mission_failures_any_extra += 1
            return False

    # Phase 3a: Deduct per-player costs from each player
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

    # Phase 3b: Deduct group extras from participants with most remaining resources
    if group_extras.typed or group_extras.any_extra > 0:
        to_remove: dict = dict(group_extras.typed)
        remaining_any = group_extras.any_extra

        participants_by_resources = sorted(participants, key = lambda p: -len(p.resources))

        # Deduct typed group extras
        for resource, total in to_remove.items():
            left = total
            for player in participants_by_resources:
                while left > 0 and resource in player.resources:
                    player.resources.remove(resource)
                    left -= 1
            state.resources_consumed[resource] = state.resources_consumed.get(resource, 0) + total

        # Deduct any_extra group extras greedily
        if remaining_any > 0:
            for player in participants_by_resources:
                resources_by_type = Counter(player.resources)
                for resource in sorted(resources_by_type, key = lambda r: -resources_by_type[r]):
                    take = min(remaining_any, resources_by_type[resource])
                    for _ in range(take):
                        player.resources.remove(resource)
                    state.resources_consumed[resource] = state.resources_consumed.get(resource, 0) + take
                    remaining_any -= take
                    if remaining_any <= 0:
                        break
                if remaining_any <= 0:
                    break

    return True


def resolve_mission(
        state: GameState,
        mission: Mission,
        participants: list[Player],
        complication: Optional[ComplicationCard],
) -> bool:
    """
    Attempt to resolve a mission with the given participants and complication card.

    Each participant must individually meet the per-player resource requirements.
    Complication and volcano card extras are paid once by the group from pooled
    surplus. `complication` may be None when the round has no complication
    (e.g. skip_next_complication was set).

    Args:
        state: Current game state (tools, players, pending effects).
        mission: The mission being attempted.
        participants: Players contributing resources to the mission.
        complication: The complication card drawn for this attempt, or None.

    Returns:
        True if the mission succeeds and resources are deducted, False otherwise.
    """
    # Exact participant count
    if len(participants) != mission.players_count:
        return False

    # Tool availability
    for tool in mission.required_tools:
        if state.tools[tool].damaged:
            state.mission_failures_tool_damaged[tool] = (
                    state.mission_failures_tool_damaged.get(tool, 0) + 1
            )
            return False

    # Night Anxiety: need 1 non-participant, non-exhausted helper
    if complication is not None and complication.requires_extra_helper:
        helpers = [p for p in state.players if p not in participants and not p.is_exhausted]
        if not helpers:
            return False

    per_player = compute_per_player_requirements(mission, state)
    group_extras = compute_group_extras(mission, complication, participants, state)

    success = check_and_contribute(
        participants = participants,
        per_player_requirements = per_player,
        group_extras = group_extras,
        max_per_type = complication.max_resource_per_type if complication is not None else None,
        state = state,
        mission = mission,
    )

    if success and complication is not None and complication.damages_tool_on_success is not None:
        state.tools[complication.damages_tool_on_success].damaged = True

    return success
