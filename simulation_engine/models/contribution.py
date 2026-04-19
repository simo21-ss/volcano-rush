from dataclasses import dataclass


@dataclass
class CharacterContribution:
    missions_participated: int = 0
    boat_missions_participated: int = 0
    tools_repaired: int = 0
    lesser_evil_uses: int = 0
    requirement_discounts_used: int = 0
