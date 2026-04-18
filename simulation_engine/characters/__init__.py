from ..models.enums import Character
from .base import CharacterStrategy
from .builder import BuilderStrategy
from .fire_starter import FireStarterStrategy
from .craftsman import CraftsmanStrategy
from .cook import CookStrategy
from .gatherer import GathererStrategy
from .sailor import SailorStrategy


STRATEGY_REGISTRY: dict[Character, CharacterStrategy] = {
    Character.BUILDER:      BuilderStrategy(),
    Character.FIRE_STARTER: FireStarterStrategy(),
    Character.CRAFTSMAN:    CraftsmanStrategy(),
    Character.COOK:         CookStrategy(),
    Character.GATHERER:     GathererStrategy(),
    Character.SAILOR:       SailorStrategy(),
}


def get_strategy(character: Character) -> CharacterStrategy:
    return STRATEGY_REGISTRY[character]
