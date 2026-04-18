from .base import CharacterStrategy
from .builder import BuilderStrategy
from .cook import CookStrategy
from .craftsman import CraftsmanStrategy
from .fire_starter import FireStarterStrategy
from .gatherer import GathererStrategy
from .sailor import SailorStrategy
from ..models.enums import Character

STRATEGY_REGISTRY: dict[Character, CharacterStrategy] = {
    Character.BUILDER: BuilderStrategy(),
    Character.FIRE_STARTER: FireStarterStrategy(),
    Character.CRAFTSMAN: CraftsmanStrategy(),
    Character.COOK: CookStrategy(),
    Character.GATHERER: GathererStrategy(),
    Character.SAILOR: SailorStrategy(),
}


def get_strategy(character: Character) -> CharacterStrategy:
    return STRATEGY_REGISTRY[character]
