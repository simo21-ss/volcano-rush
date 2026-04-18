from ..models import Player
from ..characters import get_strategy
from ..characters.base import GatherDecision

from .feasibility import team_can_afford
from .mission_selection import vote_for_mission, decide_active_player_action
from .participant_selection import active_player_select_participants


def choose_gather(player: Player) -> GatherDecision:
    return get_strategy(player.character).gather(player)


__all__ = [
    "team_can_afford",
    "vote_for_mission",
    "decide_active_player_action",
    "active_player_select_participants",
    "choose_gather",
]
