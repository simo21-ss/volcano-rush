"""
Paired evaluation of a learned policy against the rule-based baseline.

Both policies are run on the same seeds so each game starts from an identical
deal, deck order, and volcano order, differing only in the decisions taken. That
pairing supports a McNemar test on the discordant win/loss outcomes, and Wilson
score intervals report win-rate uncertainty. Both statistics are implemented in
pure math so the engine package keeps no scientific-computing dependency.
"""

import math
from dataclasses import dataclass
from typing import Optional

from ..engine.game import run_scenario
from ..models import GameOutcome
from ..agents import MissionSelector, ParticipantSelector


# 97.5th percentile of the standard normal, for two-sided 95% intervals.
Z_95 = 1.959963984540054


@dataclass(frozen = True)
class WilsonInterval:
    point: float
    lower: float
    upper: float


@dataclass(frozen = True)
class McNemarResult:
    rl_only_wins: int       # games the RL policy won but the baseline lost
    baseline_only_wins: int  # games the baseline won but the RL policy lost
    statistic: float
    p_value: float


@dataclass
class EvaluationResult:
    player_count: int
    n_games: int
    rl_records: list
    baseline_records: list

    def _wins(self, records: list) -> int:
        return sum(1 for record in records if record.outcome == GameOutcome.WIN)

    @property
    def rl_wins(self) -> int:
        return self._wins(self.rl_records)

    @property
    def baseline_wins(self) -> int:
        return self._wins(self.baseline_records)

    @property
    def rl_win_rate(self) -> float:
        return self.rl_wins / self.n_games

    @property
    def baseline_win_rate(self) -> float:
        return self.baseline_wins / self.n_games

    def win_flags(self) -> tuple:
        rl_flags = [1 if record.outcome == GameOutcome.WIN else 0 for record in self.rl_records]
        baseline_flags = [1 if record.outcome == GameOutcome.WIN else 0 for record in self.baseline_records]
        return rl_flags, baseline_flags

    def rl_win_interval(self, z: float = Z_95) -> WilsonInterval:
        return wilson_interval(self.rl_wins, self.n_games, z)

    def baseline_win_interval(self, z: float = Z_95) -> WilsonInterval:
        return wilson_interval(self.baseline_wins, self.n_games, z)

    def mcnemar(self) -> McNemarResult:
        rl_flags, baseline_flags = self.win_flags()
        return mcnemar_paired(rl_flags, baseline_flags)


def evaluate_policy(
        player_count: int,
        n_games: int,
        base_seed: int,
        mission_selector: Optional[MissionSelector] = None,
        participant_selector: Optional[ParticipantSelector] = None,
) -> EvaluationResult:
    """
    Run n_games twice on the same seeds: once with the given learned selectors,
    once with the rule-based baseline (no selectors). Returns both record sets.
    """
    rl_records = run_scenario(
        player_count = player_count,
        n_games = n_games,
        base_seed = base_seed,
        mission_selector = mission_selector,
        participant_selector = participant_selector,
    )
    baseline_records = run_scenario(
        player_count = player_count,
        n_games = n_games,
        base_seed = base_seed,
    )
    return EvaluationResult(
        player_count = player_count,
        n_games = n_games,
        rl_records = rl_records,
        baseline_records = baseline_records,
    )


def wilson_interval(wins: int, n_games: int, z: float = Z_95) -> WilsonInterval:
    """Wilson score interval for a binomial proportion."""
    if n_games == 0:
        return WilsonInterval(point = 0.0, lower = 0.0, upper = 0.0)
    proportion = wins / n_games
    denominator = 1.0 + z * z / n_games
    center = (proportion + z * z / (2 * n_games)) / denominator
    half_width = (z / denominator) * math.sqrt(proportion * (1 - proportion) / n_games + z * z / (4 * n_games * n_games))
    return WilsonInterval(point = proportion, lower = center - half_width, upper = center + half_width)


def mcnemar_paired(rl_win_flags: list, baseline_win_flags: list) -> McNemarResult:
    """
    Continuity-corrected McNemar test on paired win/loss outcomes.

    Only discordant pairs (one policy wins, the other loses on the same seed)
    carry information. The statistic follows a chi-square with one degree of
    freedom, whose survival function is erfc(sqrt(statistic / 2)).
    """
    rl_only_wins = sum(1 for rl, baseline in zip(rl_win_flags, baseline_win_flags) if rl == 1 and baseline == 0)
    baseline_only_wins = sum(1 for rl, baseline in zip(rl_win_flags, baseline_win_flags) if rl == 0 and baseline == 1)
    discordant = rl_only_wins + baseline_only_wins
    if discordant == 0:
        return McNemarResult(rl_only_wins = 0, baseline_only_wins = 0, statistic = 0.0, p_value = 1.0)

    corrected = max(0.0, abs(rl_only_wins - baseline_only_wins) - 1.0)
    statistic = corrected * corrected / discordant
    p_value = math.erfc(math.sqrt(statistic / 2.0))
    return McNemarResult(
        rl_only_wins = rl_only_wins,
        baseline_only_wins = baseline_only_wins,
        statistic = statistic,
        p_value = p_value,
    )
