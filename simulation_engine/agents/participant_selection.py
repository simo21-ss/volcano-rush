import random
from typing import Optional

from ..models import Character, Resource, MissionType, Player, GameState, Mission
from .feasibility import AffordLevel, player_afford_level

_CHARACTER_BONUS_MISSION_TYPES: dict[Character, MissionType] = {
    Character.COOK: MissionType.FOOD,
    Character.FIRE_STARTER: MissionType.FIRE,
    Character.SAILOR: MissionType.BOAT,
}


def active_player_select_participants(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
    """
    Select participants for the mission using a deterministic scoring heuristic.

    Each non-exhausted, non-active candidate is scored by _participant_score and
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


def _character_bonus_applies(character: Character, mission: Mission) -> bool:
    if character == Character.BUILDER:
        return mission.required_resources.get(Resource.WOOD, 0) >= 1
    expected_type = _CHARACTER_BONUS_MISSION_TYPES.get(character)
    return expected_type is not None and mission.mission_type == expected_type

_AFFORD_SCORE: dict[AffordLevel, int] = {
    AffordLevel.EXACT: 5,
    AffordLevel.SURPLUS: 3,
}
_COMPETITION_WEIGHT_PROBABILITY = 0.75


_COMPETITION_WEIGHT_FLOOR = -4


def _competition_penalty(candidate: Player, active_player: Player) -> int:
    """
    Semi-cooperative penalty: candidates already ahead of the active player get
    a small negative score so the active player mildly prefers not to widen a
    leader's personal-point lead. Floored at a small magnitude so the penalty
    can never override the primary feasibility signals.
    """
    lead = candidate.score - active_player.score
    if lead <= 0:
        return 0
    return max(_COMPETITION_WEIGHT_FLOOR, -(lead // 2))


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
        +10  character bonus applies to this mission (Cook/food, Fire Starter/fire,
             Sailor/boat, Builder/wood-requiring)
        +5   hand exactly matches the per-player cost (no waste)
        +3   hand covers the cost with surplus (pays group extras from complications)
        -20  is the Craftsman while a tool is damaged and no repair is scheduled
             (leave them free to repair next round)
        competition: candidate ahead of active player in score, -1 per 2 points
             of lead, floored at -4. Applied only for 75% of selection calls so
             the active player does not always optimise personal-point competition.
    """
    afford_level = player_afford_level(player, mission, state)
    if afford_level == AffordLevel.CANNOT_AFFORD:
        return None

    score = _AFFORD_SCORE[afford_level]

    if _character_bonus_applies(player.character, mission):
        score += 10

    if player.character == Character.CRAFTSMAN:
        any_tool_needs_repair = any(
            tool_state.damaged and tool_state.repair_due is None
            for tool_state in state.tools.values()
        )
        if any_tool_needs_repair:
            score -= 20

    if apply_competition and player is not active_player:
        score += _competition_penalty(player, active_player)

    return score
