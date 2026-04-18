from dataclasses import dataclass, field
from typing import Optional

from .enums import Resource, VolcanoCardName


@dataclass(frozen = True)
class BonusEffect:
    resource_discount: dict[Resource, int] = field(default_factory = dict)
    resource_discount_any: int = 0
    skip_next_complication: bool = False
    gather_bonus: int = 0
    negates_volcano_card: Optional[VolcanoCardName] = None
    repair_tool: bool = False
    no_exhaustion: bool = False
    protect_next_failure: bool = False
    boat_part: bool = False
