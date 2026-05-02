from typing import Optional

from ..models import (
    GameState, Mission, ComplicationCard, VolcanoCard, MissionRequirement,
)


def compute_per_player_requirements(mission: Mission, state: GameState) -> MissionRequirement:
    """
    Compute the base per-player mission requirements.

    Character ability discounts are applied per-player inside check_and_contribute.

    Args:
        mission: The mission being attempted.
        state: Current game state (unused here; accepted for signature symmetry
               with compute_complication_extras and compute_volcano_extras).

    Returns:
        Per-player base requirements. Each participant must individually meet these.
    """
    return MissionRequirement(
        typed = dict(mission.required_resources),
        any_extra = 0,
    )


def compute_complication_extras(mission: Mission, complication: Optional[ComplicationCard]) -> MissionRequirement:
    """
    Compute the per-participant complication extras.

    Each participant pays these individually in addition to the base per-player
    cost. extra_per_participant is folded into any_extra: each participant pays
    that many any-resources once, yielding the same total as the former pooled
    participants * extra_per_participant, but distributed across participants.

    Args:
        mission: The mission being attempted (used for conditional gating).
        complication: The complication card drawn, or None if the round has no
                      complication (e.g. skip_next_complication).

    Returns:
        Per-participant extra requirements.
    """
    if complication is None:
        return MissionRequirement(typed = {}, any_extra = 0)

    resource_requirements: dict = {}
    for resource, amount in complication.extra_resources.items():
        if complication.conditional_on_resource is None or complication.conditional_on_resource in mission.required_resources:
            resource_requirements[resource] = resource_requirements.get(resource, 0) + amount

    any_extra = complication.extra_resources_any + complication.extra_per_participant

    return MissionRequirement(typed = resource_requirements, any_extra = any_extra)


def compute_volcano_extras(mission: Mission, state: GameState) -> MissionRequirement:
    """
    Compute the per-participant extras from the pending volcano card.

    Each participant pays these individually on top of their base and complication
    costs, matching how complication extras are charged. A conditional card (e.g.
    Rain and Mud) only applies when the mission requires the named resource.

    Args:
        mission: The mission being attempted (used for conditional gating).
        state: Current game state (pending volcano card, etc.).

    Returns:
        Per-participant volcano extras with typed resource costs.
    """
    resource_requirements: dict = {}

    if state.pending_volcano_card is not None:
        volcano_card = VolcanoCard.get(state.pending_volcano_card)
        base_resources = mission.required_resources
        for resource, amount in volcano_card.extra_resources.items():
            if volcano_card.conditional_on_resource is None or volcano_card.conditional_on_resource in base_resources:
                resource_requirements[resource] = resource_requirements.get(resource, 0) + amount

    return MissionRequirement(typed = resource_requirements, any_extra = 0)
