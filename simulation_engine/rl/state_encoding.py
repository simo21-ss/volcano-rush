"""
Compact discrete state encoders for tabular reinforcement learning.

The full Volcano Rush game state is far too large to enumerate (well over 10^50
distinct configurations), so a tabular agent cannot key its Q-table on the raw
state. These encoders project the state down to a small tuple of small integers
that captures only the information relevant to one decision. Each encoder is a
deterministic, lossy abstraction: many raw states collapse to the same key, and
that is the point - it lets a Q-table generalise across them.

Two decisions are encoded:
  - MissionStateEncoder: the active player's choice of which mission to attempt.
  - ParticipantStateEncoder: a per-candidate view of whether to staff a player.
"""

from dataclasses import dataclass
from typing import ClassVar

from ..models import (
    GameState, Player, Mission, MissionType,
    VolcanoCardName, BOAT_PART_ORDER, Character,
)
from ..characters import get_strategy
from ..agents.feasibility import AffordLevel, team_can_afford, player_afford_level


# A state key is a tuple of small non-negative integers, used directly as a
# dictionary key into a sparse Q-table.
StateKey = tuple[int, ...]


def bucket_index(value: int, edges: tuple[int, ...]) -> int:
    """
    Map a value to the number of edges it strictly exceeds.

    With edges (4, 8, 12): values <= 4 map to 0, 5..8 map to 1, 9..12 map to 2,
    and 13+ map to 3. The result is always in 0 .. len(edges).
    """
    return sum(1 for edge in edges if value > edge)


def next_needed_boat_part(state: GameState):
    """Return the first boat part in build order not yet built, or None if done."""
    for boat_part in BOAT_PART_ORDER:
        if boat_part not in state.boat_parts_built:
            return boat_part
    return None


@dataclass(frozen = True)
class MissionStateEncoder:
    """
    Encode the mission-selection decision into a 7-feature key.

    Features (in tuple order) and their cardinalities:
      0. volcano urgency bucket of len(volcano_deck)            len(edges) + 1 (= 4)
      1. boat parts already built, clamped to max_boat_parts    max_boat_parts + 1 (= 6)
      2. panic pending flag                                     2
      3. next-needed boat part status                           3
         (0 absent from offer, 1 present but team cannot afford, 2 present and affordable)
      4. any boat mission currently affordable                  2
      5. bitmask of non-boat categories on offer {FIRE,FOOD,SHELTER}  8
      6. active player can individually afford some offered mission  2

    Default cardinality: 4 * 6 * 2 * 3 * 2 * 8 * 2 = 4608 keys. Many of these are
    unreachable in real play, so the number of visited keys is far smaller.
    """

    urgency_bucket_edges: tuple[int, ...] = (4, 8, 12)
    max_boat_parts: int = 5

    NON_BOAT_CATEGORIES: ClassVar[tuple[MissionType, ...]] = (
        MissionType.FIRE, MissionType.FOOD, MissionType.SHELTER,
    )

    def _available_missions(self, state: GameState) -> list:
        """Active missions after the Panic boat ban, matching vote_for_mission."""
        if VolcanoCardName.PANIC in state.pending_volcano_cards:
            return [
                mission_name for mission_name in state.active_missions
                if Mission.catalog[mission_name].mission_type != MissionType.BOAT
            ]
        return list(state.active_missions)

    def encode(self, active_player: Player, state: GameState) -> StateKey:
        available = self._available_missions(state)

        urgency = bucket_index(len(state.volcano_deck), self.urgency_bucket_edges)
        boat_progress = min(len(state.boat_parts_built), self.max_boat_parts)
        panic = 1 if VolcanoCardName.PANIC in state.pending_volcano_cards else 0

        next_needed = next_needed_boat_part(state)
        if next_needed is None or next_needed not in available:
            next_boat_status = 0
        elif team_can_afford(Mission.catalog[next_needed], state):
            next_boat_status = 2
        else:
            next_boat_status = 1

        any_feasible_boat = 1 if any(
            Mission.catalog[mission_name].mission_type == MissionType.BOAT
            and team_can_afford(Mission.catalog[mission_name], state)
            for mission_name in available
        ) else 0

        category_bitmask = 0
        for bit_index, category in enumerate(self.NON_BOAT_CATEGORIES):
            if any(Mission.catalog[mission_name].mission_type == category for mission_name in available):
                category_bitmask |= (1 << bit_index)

        active_can_afford_any = 1 if any(
            player_afford_level(active_player, Mission.catalog[mission_name], state) != AffordLevel.CANNOT_AFFORD
            for mission_name in available
        ) else 0

        return (
            urgency,
            boat_progress,
            panic,
            next_boat_status,
            any_feasible_boat,
            category_bitmask,
            active_can_afford_any,
        )

    def cardinality(self) -> int:
        urgency_levels = len(self.urgency_bucket_edges) + 1
        boat_progress_levels = self.max_boat_parts + 1
        category_combinations = 2 ** len(self.NON_BOAT_CATEGORIES)
        return urgency_levels * boat_progress_levels * 2 * 3 * 2 * category_combinations * 2


@dataclass(frozen = True)
class ParticipantStateEncoder:
    """
    Encode one candidate's staffing decision into a 6-feature key.

    Features (in tuple order) and their cardinalities:
      0. affordability of this mission for the candidate        3
         (0 cannot afford, 1 exact, 2 surplus)
      1. candidate's character ability is active on this mission 2
      2. candidate is the Craftsman while a tool needs repair    2
      3. candidate's personal-score lead over the active player  3
         (0 behind or tied, 1 ahead by 1..near_lead, 2 ahead by more)
      4. mission is a boat mission                               2
      5. candidate is the active player (the captain)            2

    Default cardinality: 3 * 2 * 2 * 3 * 2 * 2 = 144 keys.
    """

    near_lead: int = 2

    _AFFORD_INDEX: ClassVar[dict] = {
        AffordLevel.CANNOT_AFFORD: 0,
        AffordLevel.EXACT: 1,
        AffordLevel.SURPLUS: 2,
    }

    def encode(self, candidate: Player, active_player: Player, mission: Mission, state: GameState) -> StateKey:
        afford_index = self._AFFORD_INDEX[player_afford_level(candidate, mission, state)]

        ability_active = 1 if get_strategy(candidate.character).has_active_ability_on(mission) else 0

        craftsman_needs_repair = 1 if (
            candidate.character == Character.CRAFTSMAN
            and any(
                tool_state.damaged and not tool_state.under_repair
                for tool_state in state.tools.values()
            )
        ) else 0

        lead = candidate.score - active_player.score
        if lead <= 0:
            lead_bucket = 0
        elif lead <= self.near_lead:
            lead_bucket = 1
        else:
            lead_bucket = 2

        mission_is_boat = 1 if mission.mission_type == MissionType.BOAT else 0
        is_active_player = 1 if candidate is active_player else 0

        return (
            afford_index,
            ability_active,
            craftsman_needs_repair,
            lead_bucket,
            mission_is_boat,
            is_active_player,
        )

    def cardinality(self) -> int:
        return 3 * 2 * 2 * 3 * 2 * 2
