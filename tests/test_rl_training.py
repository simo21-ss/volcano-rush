import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from simulation_engine.engine.game import run_game
from simulation_engine.models.enums import GameOutcome
from simulation_engine.rl.q_agent import Schedules, UpdateRule
from simulation_engine.rl.policies import MissionPolicy, ParticipantPolicy
from simulation_engine.rl.training import TrainingConfig, train_self_play


def small_config(**overrides) -> TrainingConfig:
    defaults = {
        "player_count": 6,
        "n_episodes": 300,
        "base_seed": 1,
        "schedules": Schedules(epsilon_decay_episodes = 200),
        "exploration_seed": 3,
    }
    defaults.update(overrides)
    return TrainingConfig(**defaults)


class TestTrainSelfPlay:

    def test_learns_both_streams_and_records_diagnostics(self):
        result = train_self_play(small_config())
        assert result.mission_agent is not None
        assert result.participant_agent is not None
        assert result.mission_agent.visited_state_count > 0
        assert result.participant_agent.visited_state_count > 0
        assert len(result.checkpoint_episodes) == len(result.win_rate_curve)
        assert len(result.win_rate_curve) > 0
        assert all(0.0 <= win_rate <= 1.0 for win_rate in result.win_rate_curve)

    def test_mission_only_leaves_participant_agent_unset(self):
        result = train_self_play(small_config(learn_mission = True, learn_participant = False))
        assert result.mission_agent is not None
        assert result.participant_agent is None

    def test_participant_only_leaves_mission_agent_unset(self):
        result = train_self_play(small_config(learn_mission = False, learn_participant = True))
        assert result.mission_agent is None
        assert result.participant_agent is not None

    def test_requires_at_least_one_learned_stream(self):
        with pytest.raises(ValueError):
            train_self_play(small_config(learn_mission = False, learn_participant = False))

    def test_is_reproducible_for_equal_config(self):
        first = train_self_play(small_config())
        second = train_self_play(small_config())
        assert first.win_rate_curve == second.win_rate_curve
        assert first.mission_agent.visited_state_count == second.mission_agent.visited_state_count

    def test_greedy_policies_plug_into_engine(self):
        config = small_config()
        result = train_self_play(config)
        mission_selector = MissionPolicy(result.mission_agent, config.mission_encoder).greedy_selector()
        participant_selector = ParticipantPolicy(result.participant_agent, config.participant_encoder).greedy_selector()
        record = run_game(
            player_count = 6,
            mission_selector = mission_selector,
            participant_selector = participant_selector,
        )
        assert record.outcome in (GameOutcome.WIN, GameOutcome.LOSS)
