import random
from typing import Optional

from ..models import Character, Player, GameState, Mission
from ..characters import get_strategy
from .feasibility import AffordLevel, player_afford_level


# Scoring weights
_AFFORD_SCORE: dict[AffordLevel, int] = {
    AffordLevel.EXACT: 3,
    AffordLevel.SURPLUS: 5,
}
_ACTIVE_ABILITY_BONUS = 10
_CRAFTSMAN_REPAIR_PENALTY = -20
_COMPETITION_WEIGHT_PROBABILITY = 0.75
_COMPETITION_WEIGHT_FLOOR = -8


def active_player_select_participants(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
    """
    Select participants for the mission using a deterministic scoring heuristic.

    Each non-exhausted, non-active candidate is scored by _participant_score, and
    the top-N are taken (N = mission.players_count). Ties are broken by the
    candidate's original index in state.players for stable, reproducible selection.
    The active player is prepended to the shortlist when their score is non-negative,
    matching the behaviour that the captain usually joins their own mission.

    Args:
        active_player: The player whose turn it is to lead this round.
        mission: The mission to staff.
        state: Current game state.

    Returns:
        A list of up to mission.players_count Player objects.
    """
    needed = mission.players_count
    apply_competition = random.random() < _COMPETITION_WEIGHT_PROBABILITY

    scored: list[tuple[int, int, Player]] = []
    for index, player in enumerate(state.players):
        if player is active_player or player.is_exhausted:
            continue
        score = _participant_score(player, mission, state, active_player, apply_competition)
        if score is None:
            continue
        scored.append((score, index, player))

    scored.sort(key = lambda entry: (-entry[0], entry[1]))
    ranked = [player for _, _, player in scored]

    if not active_player.is_exhausted:
        active_afford = player_afford_level(active_player, mission, state)
        if active_afford != AffordLevel.CANNOT_AFFORD:
            ranked = [active_player] + ranked

    return ranked[:needed]


def _competition_penalty(candidate: Player, active_player: Player) -> int:
    """
    Semi-cooperative penalty: candidates already ahead of the active player get
    a negative score so the active player prefers not to widen a leader's
    personal-point lead. Each point of lead subtracts 1 from the candidate's
    score, floored at _COMPETITION_WEIGHT_FLOOR so the penalty cannot override
    the character-ability or Craftsman-repair signals.
    """
    lead = candidate.score - active_player.score
    if lead <= 0:
        return 0
    return max(_COMPETITION_WEIGHT_FLOOR, -lead)


def _participant_score(
        player: Player,
        mission: Mission,
        state: GameState,
        active_player: Player,
        apply_competition: bool,
) -> Optional[int]:
    """
    Score a candidate participant for mission staffing.

    Higher scores are preferred. Returns None when the candidate cannot fully
    pay for the mission's per-player base cost. A player who cannot pay should
    not be selected - they would just fail the mission and waste an exhaustion
    slot.

    Scoring breakdown (for candidates who can afford):
        +_ACTIVE_ABILITY_BONUS  character's ability is relevant to this mission
                                (Cook/food, Fire Starter/fire, Sailor/boat,
                                Builder/shelter+boat-with-wood)
        +_AFFORD_SCORE[SURPLUS] hand covers the cost with surplus resources
                                (absorbs per-participant complication or volcano extras)
        +_AFFORD_SCORE[EXACT]   hand exactly matches the base cost (no surplus,
                                so fails any complication with extras)
        +_CRAFTSMAN_REPAIR_PENALTY  Craftsman while a tool is damaged and no repair
                                    is scheduled (leave them free to repair next round)
        competition: candidate ahead of active player in score, -1 per point
             of lead, floored at _COMPETITION_WEIGHT_FLOOR. Applied only for
             _COMPETITION_WEIGHT_PROBABILITY of selection calls so the active
             player does not always optimise personal-point competition.
    """
    afford_level = player_afford_level(player, mission, state)
    if afford_level == AffordLevel.CANNOT_AFFORD:
        return None

    score = _AFFORD_SCORE[afford_level]

    if get_strategy(player.character).has_active_ability_on(mission):
        score += _ACTIVE_ABILITY_BONUS

    if player.character == Character.CRAFTSMAN:
        any_tool_needs_repair = any(
            tool_state.damaged and not tool_state.under_repair
            for tool_state in state.tools.values()
        )
        if any_tool_needs_repair:
            score += _CRAFTSMAN_REPAIR_PENALTY

    if apply_competition and player is not active_player:
        score += _competition_penalty(player, active_player)

    return score
