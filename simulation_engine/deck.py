import random
from typing import Optional

from .models import Resource, ComplicationCardName, VolcanoCardName, MissionName, GameState
from .initialization import _prepare_resource_deck


def draw_resource(state: GameState) -> Resource:
    if not state.resource_deck:
        state.resource_deck = _prepare_resource_deck()

    return state.resource_deck.pop()


def draw_complication(state: GameState) -> ComplicationCardName:
    return random.choice(state.complication_deck)


def draw_volcano(state: GameState) -> VolcanoCardName:
    return state.volcano_deck.pop()


def draw_mission(state: GameState) -> Optional[MissionName]:
    return state.mission_pool.pop() if state.mission_pool else None
