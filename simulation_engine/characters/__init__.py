from ..models.enums import Character
from .base import CharacterStrategy
from .builder import BuilderStrategy
from .fire_starter import FireStarterStrategy
from .craftsman import CraftsmanStrategy
from .cook import CookStrategy
from .thief import ThiefStrategy
from .sailor import SailorStrategy


_STRATEGY_REGISTRY: dict[Character, CharacterStrategy] = {
    Character.BUILDER:      BuilderStrategy(),
    Character.FIRE_STARTER: FireStarterStrategy(),
    Character.CRAFTSMAN:    CraftsmanStrategy(),
    Character.COOK:         CookStrategy(),
    Character.THIEF:        ThiefStrategy(),
    Character.SAILOR:       SailorStrategy(),
}


def get_strategy(character: Character) -> CharacterStrategy:
    return _STRATEGY_REGISTRY[character]
