import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.rl.q_agent import UpdateRule, Schedules, TabularAgent
from simulation_engine.rl.trajectory import (
    Transition, TrajectoryRecorder, MISSION_DECISION, PARTICIPANT_DECISION,
)


def constant_schedules(alpha: float = 0.5, gamma: float = 0.9) -> Schedules:
    """Schedules with a fixed learning rate and no exploration, for exact-math tests."""
    return Schedules(
        alpha_start = alpha,
        alpha_end = alpha,
        gamma = gamma,
        epsilon_start = 0.0,
        epsilon_end = 0.0,
        epsilon_decay_episodes = 1,
    )


# ── Schedules ──────────────────────────────────────────────────────────────────

class TestSchedules:

    def test_endpoints(self):
        schedules = Schedules(
            alpha_start = 0.5, alpha_end = 0.05,
            epsilon_start = 1.0, epsilon_end = 0.02,
            epsilon_decay_episodes = 1000,
        )
        assert schedules.alpha(0) == 0.5
        assert schedules.epsilon(0) == 1.0
        assert schedules.alpha(1000) == 0.05
        assert schedules.epsilon(1000) == 0.02
        # Held flat past the decay horizon.
        assert schedules.epsilon(5000) == 0.02

    def test_midpoint_is_linear(self):
        schedules = Schedules(epsilon_start = 1.0, epsilon_end = 0.0, epsilon_decay_episodes = 100)
        assert abs(schedules.epsilon(50) - 0.5) < 1e-12

    def test_set_episode_updates_current_rates(self):
        agent = TabularAgent(2, Schedules(epsilon_start = 1.0, epsilon_end = 0.02, epsilon_decay_episodes = 100), UpdateRule.Q_LEARNING, exploration_seed = 1)
        agent.set_episode(100)
        assert agent.current_epsilon == 0.02


# ── TD update closed-form (Q-learning and SARSA) ──────────────────────────────

class TestUpdates:

    def test_terminal_update_has_no_bootstrap(self):
        agent = TabularAgent(2, constant_schedules(alpha = 0.5), UpdateRule.Q_LEARNING, exploration_seed = 0)
        transition = Transition(
            state_key = (0,), action_index = 0, reward = 1.0,
            next_state_key = None, next_legal_action_indices = None, next_action_index = None, done = True,
        )
        td_error = agent.apply_update(transition)
        # target = reward = 1.0; Q starts at 0; new Q = 0 + 0.5 * (1.0 - 0) = 0.5
        assert abs(td_error - 1.0) < 1e-12
        assert abs(agent.action_values((0,))[0] - 0.5) < 1e-12

    def test_q_learning_bootstraps_on_max_next_action(self):
        agent = TabularAgent(2, constant_schedules(alpha = 0.5, gamma = 0.9), UpdateRule.Q_LEARNING, exploration_seed = 0)
        # Seed the next state so action 0 is best (2.0) and action 1 is worse (1.0).
        agent.q_row((1,))[:] = [2.0, 1.0]
        transition = Transition(
            state_key = (0,), action_index = 0, reward = 1.0,
            next_state_key = (1,), next_legal_action_indices = [0, 1], next_action_index = 1, done = False,
        )
        agent.apply_update(transition)
        # target = 1.0 + 0.9 * max(2.0, 1.0) = 2.8; new Q = 0 + 0.5 * 2.8 = 1.4
        assert abs(agent.action_values((0,))[0] - 1.4) < 1e-12

    def test_sarsa_bootstraps_on_taken_next_action(self):
        agent = TabularAgent(2, constant_schedules(alpha = 0.5, gamma = 0.9), UpdateRule.SARSA, exploration_seed = 0)
        agent.q_row((1,))[:] = [2.0, 1.0]
        transition = Transition(
            state_key = (0,), action_index = 0, reward = 1.0,
            next_state_key = (1,), next_legal_action_indices = [0, 1], next_action_index = 1, done = False,
        )
        agent.apply_update(transition)
        # target = 1.0 + 0.9 * Q(next, action 1 taken) = 1.0 + 0.9 * 1.0 = 1.9; new Q = 0.5 * 1.9 = 0.95
        assert abs(agent.action_values((0,))[0] - 0.95) < 1e-12


# ── action selection ──────────────────────────────────────────────────────────

class TestSelection:

    def test_epsilon_zero_is_deterministic_greedy(self):
        agent = TabularAgent(3, constant_schedules(), UpdateRule.Q_LEARNING, exploration_seed = 0)
        agent.q_row((0,))[:] = [0.0, 5.0, 1.0]
        for _ in range(20):
            assert agent.select_index_training((0,), [0, 1, 2]) == 1

    def test_epsilon_one_is_reproducible_across_equal_seeds(self):
        schedules = Schedules(epsilon_start = 1.0, epsilon_end = 1.0, epsilon_decay_episodes = 1)
        first = TabularAgent(4, schedules, UpdateRule.Q_LEARNING, exploration_seed = 123)
        second = TabularAgent(4, schedules, UpdateRule.Q_LEARNING, exploration_seed = 123)
        first_choices = [first.select_index_training((0,), [0, 1, 2, 3]) for _ in range(50)]
        second_choices = [second.select_index_training((0,), [0, 1, 2, 3]) for _ in range(50)]
        assert first_choices == second_choices

    def test_greedy_breaks_ties_by_lowest_index(self):
        agent = TabularAgent(3, constant_schedules(), UpdateRule.Q_LEARNING, exploration_seed = 0)
        # All zeros: greedy must pick the lowest legal index deterministically.
        assert agent.select_index_greedy((9,), [2, 0, 1]) == 2  # first in the legal list when tied
        agent.q_row((9,))[:] = [1.0, 1.0, 0.0]
        assert agent.select_index_greedy((9,), [0, 1, 2]) == 0

    def test_greedy_does_not_touch_global_random(self):
        agent = TabularAgent(2, constant_schedules(), UpdateRule.Q_LEARNING, exploration_seed = 0)
        agent.q_row((0,))[:] = [0.0, 1.0]
        random.seed(42)
        state_before = random.getstate()
        agent.select_index_greedy((0,), [0, 1])
        assert random.getstate() == state_before


# ── trajectory stitching ──────────────────────────────────────────────────────

class TestTrajectoryRecorder:

    def test_single_decision_becomes_terminal_transition(self):
        recorder = TrajectoryRecorder()
        recorder.record_decision(MISSION_DECISION, (1,), action_index = 2, legal_action_indices = [0, 2])
        transitions = recorder.finalize(terminal_reward = 1.0)
        mission_transitions = transitions[MISSION_DECISION]
        assert len(mission_transitions) == 1
        assert mission_transitions[0].done is True
        assert abs(mission_transitions[0].reward - 1.0) < 1e-12
        assert mission_transitions[0].next_state_key is None

    def test_consecutive_decisions_stitch_with_accumulated_reward(self):
        recorder = TrajectoryRecorder()
        recorder.record_decision(MISSION_DECISION, (0,), action_index = 0, legal_action_indices = [0, 1])
        recorder.add_shaping_reward(0.1)
        recorder.record_decision(MISSION_DECISION, (1,), action_index = 1, legal_action_indices = [1])
        transitions = recorder.finalize(terminal_reward = -1.0)
        mission_transitions = transitions[MISSION_DECISION]
        assert len(mission_transitions) == 2

        first = mission_transitions[0]
        assert first.done is False
        assert first.next_state_key == (1,)
        assert first.next_action_index == 1
        assert first.next_legal_action_indices == [1]
        assert abs(first.reward - 0.1) < 1e-12

        last = mission_transitions[1]
        assert last.done is True
        assert abs(last.reward - (-1.0)) < 1e-12

    def test_streams_are_independent(self):
        recorder = TrajectoryRecorder()
        recorder.record_decision(MISSION_DECISION, (0,), 0, [0, 1])
        recorder.record_decision(PARTICIPANT_DECISION, (5,), 1, [0, 1])
        recorder.record_decision(PARTICIPANT_DECISION, (6,), 0, [0, 1])
        recorder.add_shaping_reward(0.1)
        recorder.record_decision(MISSION_DECISION, (1,), 1, [0, 1])
        transitions = recorder.finalize(terminal_reward = 1.0)
        # Mission: one stitched + one terminal. Participant: one stitched + one terminal.
        assert len(transitions[MISSION_DECISION]) == 2
        assert len(transitions[PARTICIPANT_DECISION]) == 2
