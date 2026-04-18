from ..models import Player


def apply_exhaustion(players: list[Player], current_round: int, extra_rounds: int = 0) -> None:
    for player in players:
        player.exhausted_until = current_round + 1 + extra_rounds
        player.is_exhausted = True
