from dataclasses import dataclass
from typing import ClassVar


@dataclass
class CharacterContribution:
    WEIGHTS: ClassVar[dict[str, float]] = {
        "missions_participated":      1.0,
        "boat_missions_participated": 0.5,
        "tools_repaired":             3.0,
        "lesser_evil_uses":           2.0,
        "requirement_discounts_used": 2.0,
    }

    missions_participated:      int   = 0
    boat_missions_participated: int   = 0
    tools_repaired:             int   = 0
    lesser_evil_uses:           int   = 0
    requirement_discounts_used: int   = 0
    group_win_effect:           float = 0.0

    def raw_score(self) -> float:
        return (self.WEIGHTS["missions_participated"] * self.missions_participated
              + self.WEIGHTS["boat_missions_participated"] * self.boat_missions_participated
              + self.WEIGHTS["tools_repaired"] * self.tools_repaired
              + self.WEIGHTS["lesser_evil_uses"] * self.lesser_evil_uses
              + self.WEIGHTS["requirement_discounts_used"] * self.requirement_discounts_used)

    @staticmethod
    def compute_group_win_effects(contributions: list["CharacterContribution"]) -> None:
        raw_scores = [contribution.raw_score() for contribution in contributions]
        total = sum(raw_scores)
        for contribution, raw in zip(contributions, raw_scores):
            contribution.group_win_effect = raw / total if total > 0 else 0.0
