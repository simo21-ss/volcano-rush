from ..models import GameState, Player


def refresh_exhaustion(state: GameState) -> None:
    for player in state.players:
        player.is_exhausted = state.round <= player.exhausted_until


def apply_exhaustion(players: list[Player], current_round: int, extra_rounds: int = 0) -> None:
    for player in players:
        player.exhausted_until = current_round + 1 + extra_rounds
        player.is_exhausted = True


def update_tool_repairs(state: GameState) -> None:
    for tool, tool_state in state.tools.items():
        if tool_state.repair_due is not None and tool_state.repair_due <= state.round:
            tool_state.damaged = False
            tool_state.repair_due = None
            state.tool_repairs[tool] = state.tool_repairs.get(tool, 0) + 1
