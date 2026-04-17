import random
from abc import ABC, abstractmethod
from collections import Counter
from typing import Optional

from ..models import (
    Character, ActivePlayerAction, MissionType, MissionName,
    BOAT_PART_ORDER, Player, GameState, Mission, MissionRequirement,
)


def get_next_needed_boat_part(state: GameState) -> Optional[MissionName]:
    reachable = set(state.active_missions) | set(state.mission_pool) | state.boat_parts_built
    for mission_name in BOAT_PART_ORDER:
        if mission_name in reachable and mission_name not in state.boat_parts_built:
            return mission_name
    return None


class CharacterStrategy(ABC):

    @property
    @abstractmethod
    def character(self) -> Character:
        ...

    # ── Individual player decisions ─────────────────────────────────

    def preferred_mission(self, active_missions: list[MissionName]) -> Optional[MissionName]:
        return None

    def active_player_decide_action(
        self,
        active_player: Player,
        state:         GameState,
    ) -> ActivePlayerAction:
        volcano_is_urgent = len(state.volcano_deck) <= state.urgent_volcano_threshold

        active_boat_missions = [
            mission_name for mission_name in state.active_missions
            if Mission.catalog[mission_name].mission_type == MissionType.BOAT
        ]
        all_active_are_boat_parts = len(active_boat_missions) == len(state.active_missions)
        next_needed = get_next_needed_boat_part(state)
        next_needed_not_active = next_needed not in state.active_missions

        if all_active_are_boat_parts and next_needed_not_active:
            if active_player.resources and not volcano_is_urgent:
                return ActivePlayerAction.SHUFFLE_MISSIONS
            return ActivePlayerAction.CHOOSE_MISSION

        no_boat_parts_visible = len(active_boat_missions) == 0
        if no_boat_parts_visible and not volcano_is_urgent:
            if active_player.resources and random.random() < 0.25:
                return ActivePlayerAction.SHUFFLE_MISSIONS

        return ActivePlayerAction.CHOOSE_MISSION

    def active_player_select_participants(
        self,
        active_player: Player,
        mission:       Mission,
        state:         GameState,
    ) -> list[Player]:
        needed = mission.players_count

        def can_afford(player: Player) -> bool:
            resources_by_type = Counter(player.resources)
            for resource, amount in mission.required_resources.items():
                if resources_by_type.get(resource, 0) < amount:
                    return False
            return True

        affordable = [
            player for player in state.players
            if player is not active_player and not player.is_exhausted and can_afford(player)
        ]
        fallback = [
            player for player in state.players
            if player is not active_player and not player.is_exhausted
            and not can_afford(player) and len(player.resources) >= 1
        ]

        random.shuffle(affordable)
        random.shuffle(fallback)

        if not active_player.is_exhausted and can_afford(active_player):
            affordable = [active_player] + affordable

        selected = affordable[:needed]
        if len(selected) < needed:
            remaining_slots = needed - len(selected)
            selected = selected + fallback[:remaining_slots]

        return selected

    def gather_amount(self, player: Player) -> int:
        return 1

    def take_gathering_action(
        self,
        player: Player,
        state:  GameState,
    ) -> bool:
        return True

    # ── Mission participation modifiers ─────────────────────────────

    def requirement_discount(
        self,
        mission:      Mission,
        requirements: MissionRequirement,
    ) -> MissionRequirement:
        return requirements

    def complication_draw_count(self, mission: Mission) -> int:
        return 1

    def mission_success_bonus_points(self, mission: Mission) -> int:
        return 0

    def post_gather_exhaustion(self, base_amount: int) -> bool:
        return False
