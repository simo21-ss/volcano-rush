import random

from ..models import Character, Player, GameState
from .base import CharacterStrategy


class ThiefStrategy(CharacterStrategy):

    @property
    def character(self) -> Character:
        return Character.THIEF

    def take_gathering_action(
        self,
        player: Player,
        state:  GameState,
    ) -> bool:
        if player.is_exhausted or len(player.resources) >= 3:
            return True

        valid_targets = [
            other_player for other_player in state.players
            if other_player is not player and len(other_player.resources) >= 1
        ]

        if len(valid_targets) < 2:
            return True

        from ..mechanics.exhaustion import apply_exhaustion

        chosen_targets = random.sample(valid_targets, min(3, len(valid_targets)))
        resources_stolen = 0
        for target in chosen_targets:
            stolen_resource = random.choice(target.resources)
            target.resources.remove(stolen_resource)
            player.resources.append(stolen_resource)
            resources_stolen += 1

        if resources_stolen < 3:
            remaining_targets = [
                target for target in chosen_targets
                if len(target.resources) >= 1
            ]
            if remaining_targets:
                target = random.choice(remaining_targets)
                stolen_resource = random.choice(target.resources)
                target.resources.remove(stolen_resource)
                player.resources.append(stolen_resource)

        apply_exhaustion([player], state.round)
        return False
