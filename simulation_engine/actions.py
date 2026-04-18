import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from .models import Resource, Player, GameState
from .mechanics import apply_exhaustion
from .deck import draw_resource


class PlayerAction(Enum):
    SHUFFLE_MISSIONS = "shuffle_missions"
    GATHER = "gather"
    REPAIR = "repair"


class NonParticipantAction(ABC):
    action_type: ClassVar[PlayerAction]

    @abstractmethod
    def execute(self, player: Player, state: GameState) -> None:
        ...


@dataclass(frozen = True)
class GatherAction(NonParticipantAction):
    action_type: ClassVar[PlayerAction] = PlayerAction.GATHER
    amount: int = 1
    causes_exhaustion: bool = False

    def execute(self, player: Player, state: GameState) -> None:
        gather_bonus = state.pending_bonus.gather_bonus if state.pending_bonus else 0
        total = self.amount + gather_bonus
        for _ in range(total):
            player.resources.append(draw_resource(state))
        if self.causes_exhaustion:
            apply_exhaustion([player], state.round)


class RepairAction(NonParticipantAction):
    action_type: ClassVar[PlayerAction] = PlayerAction.REPAIR

    def execute(self, player: Player, state: GameState) -> None:
        repairable_tool = next(
            tool for tool, tool_state in state.tools.items()
            if tool_state.damaged and tool_state.repair_due is None
        )
        state.tools[repairable_tool].repair_due = state.round + 2
        player.resources.remove(Resource.STONE)
        player.score += 1
        player.contribution.tools_repaired += 1


class ShuffleMissionsAction:
    action_type: ClassVar[PlayerAction] = PlayerAction.SHUFFLE_MISSIONS

    def execute(self, active_player: Player, state: GameState) -> None:
        resource_to_discard = random.choice(active_player.resources)
        active_player.resources.remove(resource_to_discard)
        random.shuffle(state.mission_pool)
