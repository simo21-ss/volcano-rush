import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from simulation_engine.rl.q_agent import Schedules, UpdateRule, TabularAgent
from simulation_engine.rl.evaluation import (
    evaluate_policy, wilson_interval, mcnemar_paired,
)
from simulation_engine.rl.persistence import save_agent, load_agent, load_metadata


# ── Wilson interval ─────────────────────────────────────────────────────────

class TestWilsonInterval:

    def test_brackets_point_estimate(self):
        interval = wilson_interval(35, 100)
        assert interval.lower < interval.point < interval.upper
        assert abs(interval.point - 0.35) < 1e-12
        assert 0.0 <= interval.lower <= interval.upper <= 1.0

    def test_more_games_tighten_the_interval(self):
        narrow = wilson_interval(350, 1000)
        wide = wilson_interval(35, 100)
        assert (narrow.upper - narrow.lower) < (wide.upper - wide.lower)

    def test_zero_games_is_degenerate(self):
        interval = wilson_interval(0, 0)
        assert interval.point == 0.0 and interval.lower == 0.0 and interval.upper == 0.0


# ── McNemar ──────────────────────────────────────────────────────────────────

class TestMcNemar:

    def test_no_discordant_pairs_is_not_significant(self):
        result = mcnemar_paired([1, 0, 1, 0], [1, 0, 1, 0])
        assert result.rl_only_wins == 0
        assert result.baseline_only_wins == 0
        assert result.p_value == 1.0

    def test_counts_discordant_pairs(self):
        # rl wins where baseline loses: indices 0, 2; baseline wins where rl loses: index 4
        rl = [1, 0, 1, 0, 0]
        baseline = [0, 0, 0, 0, 1]
        result = mcnemar_paired(rl, baseline)
        assert result.rl_only_wins == 2
        assert result.baseline_only_wins == 1

    def test_strong_one_sided_difference_is_significant(self):
        rl = [1] * 40 + [0] * 60
        baseline = [0] * 100
        result = mcnemar_paired(rl, baseline)
        assert result.rl_only_wins == 40
        assert result.baseline_only_wins == 0
        assert result.p_value < 0.001


# ── Paired evaluation ──────────────────────────────────────────────────────

class TestEvaluatePolicy:

    def test_baseline_against_itself_is_perfectly_paired(self):
        # With no learned selectors, the RL run and the baseline run are identical.
        result = evaluate_policy(player_count = 6, n_games = 20, base_seed = 5)
        assert result.n_games == 20
        rl_flags, baseline_flags = result.win_flags()
        assert rl_flags == baseline_flags
        assert result.rl_wins == result.baseline_wins
        # Identical outcomes mean no discordant pairs.
        assert result.mcnemar().p_value == 1.0


# ── Persistence round-trip ───────────────────────────────────────────────────

class TestPersistence:

    def test_save_and_load_round_trips_q_values(self, tmp_path):
        agent = TabularAgent(5, Schedules(), UpdateRule.SARSA, exploration_seed = 1)
        agent.q_row((1, 2, 0, 1, 0, 3, 1))[:] = [0.5, -0.2, 1.3, 0.0, 0.7]
        agent.q_row((0, 0, 1, 2, 1, 0, 0))[:] = [-1.0, 2.0, 0.0, 0.0, 0.0]

        stem = tmp_path / "mission_sarsa_pc6"
        save_agent(agent, stem, metadata = {"decision": "mission", "player_count": 6})

        loaded = load_agent(stem)
        assert loaded.action_cardinality == 5
        assert loaded.update_rule == UpdateRule.SARSA
        assert loaded.visited_state_count == 2
        assert np.allclose(loaded.action_values((1, 2, 0, 1, 0, 3, 1)), [0.5, -0.2, 1.3, 0.0, 0.7])
        assert np.allclose(loaded.action_values((0, 0, 1, 2, 1, 0, 0)), [-1.0, 2.0, 0.0, 0.0, 0.0])

        meta = load_metadata(stem)
        assert meta["decision"] == "mission"
        assert meta["player_count"] == 6
        assert meta["update_rule"] == "sarsa"

    def test_empty_agent_round_trips(self, tmp_path):
        agent = TabularAgent(2, Schedules(), UpdateRule.Q_LEARNING, exploration_seed = 0)
        stem = tmp_path / "empty_agent"
        save_agent(agent, stem)
        loaded = load_agent(stem)
        assert loaded.visited_state_count == 0
        assert loaded.action_cardinality == 2
