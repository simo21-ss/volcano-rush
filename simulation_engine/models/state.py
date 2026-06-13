from dataclasses import dataclass, field
from typing import Optional

from .bonus_effects import BonusEffect
from .contribution import CharacterContribution
from .enums import Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName, GameOutcome


@dataclass
class ToolState:
    damaged: bool = False
    under_repair: bool = False


@dataclass
class Player:
    character: Character
    resources: list[Resource] = field(default_factory = list)
    is_exhausted: bool = False
    exhausted_until: int = 0
    score: int = 0
    contribution: CharacterContribution = field(default_factory = CharacterContribution)


@dataclass
class GameState:
    players: list[Player]
    active_missions: list[MissionName]
    resource_deck: list[Resource]
    complication_deck: list[ComplicationCardName]
    volcano_deck: list[VolcanoCardName]
    tools: dict[Tool, ToolState]
    boat_parts_required: int
    boat_parts_built: set[MissionName] = field(default_factory = set)
    mission_pool: list[MissionName] = field(default_factory = list)
    round: int = 0
    skip_next_complication: bool = False
    protect_next_failure: bool = False
    skip_exhaustion: bool = False
    skip_gather_this_round: bool = False
    pending_volcano_cards: list[VolcanoCardName] = field(default_factory = list)
    pending_bonus: Optional[BonusEffect] = None
    urgent_volcano_threshold: int = 4
    active_player_index: int = 0
    resources_consumed: dict[Resource, int] = field(default_factory = dict)
    mission_failures_by_resource: dict[Resource, int] = field(default_factory = dict)
    mission_failures_any_extra: int = 0
    mission_failures_tool_damaged: dict[Tool, int] = field(default_factory = dict)
    tool_repairs: dict[Tool, int] = field(default_factory = dict)

    def begin_round(self) -> Player:
        """
        Start-of-round housekeeping: bump the round counter, complete any tool
        repairs that finish this round, and refresh each player's is_exhausted
        flag from their exhausted_until timestamp. Returns the active player
        for this round.
        """
        self.round += 1

        for tool, tool_state in self.tools.items():
            if tool_state.under_repair:
                tool_state.damaged = False
                tool_state.under_repair = False
                self.tool_repairs[tool] = self.tool_repairs.get(tool, 0) + 1

        for player in self.players:
            player.is_exhausted = self.round <= player.exhausted_until

        return self.players[self.active_player_index]

    def end_round(self, completed_mission: Optional[MissionName] = None) -> Optional[GameOutcome]:
        """
        End-of-round housekeeping: consume any pending Panic card, replace a
        completed mission with a fresh draw from the pool, check the win
        condition, and rotate the active player to the next seat.

        Args:
            completed_mission: The mission name that succeeded this round, or
                               None if the round ended without a successful
                               mission (shuffle round, forfeit round, or
                               failed a mission).

        Returns:
            GameOutcome.WIN if the boat is complete, otherwise None.
        """
        self.pending_volcano_cards = [
            card_name for card_name in self.pending_volcano_cards
            if card_name != VolcanoCardName.PANIC
        ]

        self.skip_gather_this_round = False

        if completed_mission is not None:
            self.active_missions.remove(completed_mission)
            if self.mission_pool:
                self.active_missions.append(self.mission_pool.pop())

        if len(self.boat_parts_built) >= self.boat_parts_required:
            return GameOutcome.WIN

        self.active_player_index = (self.active_player_index + 1) % len(self.players)

        return None
