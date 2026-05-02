from dataclasses import dataclass
from typing import Optional

from .enums import VolcanoCardName


@dataclass(frozen = True)
class BonusEffect:
    skip_next_complication: bool = False
    gather_bonus: int = 0
    negates_volcano_card: Optional[VolcanoCardName] = None
    no_exhaustion: bool = False
    protect_next_failure: bool = False
    boat_part: bool = False
    participant_card_draws: int = 0
    empty_hand_card_draws: int = 0
