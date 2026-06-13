"""
A tabular value-based agent supporting Q-learning (off-policy) and SARSA
(on-policy) updates over a sparse Q-table.

The agent is decision-agnostic: it keys a Q-table on integer state tuples and an
action index, and knows nothing about missions or participants. Policy wrappers
(see policies.py) translate game state into state keys and action indices and
back. Exploration uses a private random.Random so it never perturbs the global
random stream the engine uses for game dynamics, keeping seeded games reproducible.
"""

import random
from dataclasses import dataclass
from enum import Enum

import numpy as np

from .state_encoding import StateKey
from .trajectory import Transition


class UpdateRule(Enum):
    Q_LEARNING = "q_learning"   # off-policy: bootstrap on the best next action
    SARSA = "sarsa"             # on-policy: bootstrap on the action actually taken next


@dataclass
class Schedules:
    """Linear learning-rate and exploration schedules over training episodes."""
    alpha_start: float = 0.5
    alpha_end: float = 0.05
    gamma: float = 0.95
    epsilon_start: float = 1.0
    epsilon_end: float = 0.02
    epsilon_decay_episodes: int = 40_000

    def _interpolate(self, start_value: float, end_value: float, episode_index: int) -> float:
        # Return exact endpoints to avoid floating-point drift at the boundaries.
        if self.epsilon_decay_episodes <= 0 or episode_index >= self.epsilon_decay_episodes:
            return end_value
        if episode_index <= 0:
            return start_value
        fraction = episode_index / self.epsilon_decay_episodes
        return start_value + (end_value - start_value) * fraction

    def alpha(self, episode_index: int) -> float:
        return self._interpolate(self.alpha_start, self.alpha_end, episode_index)

    def epsilon(self, episode_index: int) -> float:
        return self._interpolate(self.epsilon_start, self.epsilon_end, episode_index)


class TabularAgent:
    """One Q-table for one decision stream, updated by one rule."""

    def __init__(
            self,
            action_cardinality: int,
            schedules: Schedules,
            update_rule: UpdateRule,
            exploration_seed: int,
    ) -> None:
        self.action_cardinality = action_cardinality
        self.schedules = schedules
        self.update_rule = update_rule
        self._rng = random.Random(exploration_seed)
        self._table: dict[StateKey, np.ndarray] = {}
        self.current_alpha = schedules.alpha(0)
        self.current_epsilon = schedules.epsilon(0)

    # ── schedule control ──────────────────────────────────────────────────────

    def set_episode(self, episode_index: int) -> None:
        """Set the learning rate and exploration rate for the given episode."""
        self.current_alpha = self.schedules.alpha(episode_index)
        self.current_epsilon = self.schedules.epsilon(episode_index)

    # ── Q-table access ────────────────────────────────────────────────────────

    def action_values(self, state_key: StateKey) -> np.ndarray:
        """Read-only action-value row for a state (zeros for an unseen state, not stored)."""
        stored = self._table.get(state_key)
        if stored is None:
            return np.zeros(self.action_cardinality)
        return stored

    def q_row(self, state_key: StateKey) -> np.ndarray:
        """Mutable action-value row for a state, created (and stored) if unseen."""
        stored = self._table.get(state_key)
        if stored is None:
            stored = np.zeros(self.action_cardinality)
            self._table[state_key] = stored
        return stored

    @property
    def visited_state_count(self) -> int:
        return len(self._table)

    # ── action selection ──────────────────────────────────────────────────────

    def _greedy_index(self, state_key: StateKey, legal_action_indices: list[int]) -> int:
        row = self.action_values(state_key)
        best_index = legal_action_indices[0]
        best_value = row[best_index]
        for action_index in legal_action_indices[1:]:
            if row[action_index] > best_value:
                best_value = row[action_index]
                best_index = action_index
        return best_index

    def select_index_training(self, state_key: StateKey, legal_action_indices: list[int]) -> int:
        """Epsilon-greedy selection using the private RNG (for training rollouts)."""
        if self._rng.random() < self.current_epsilon:
            return self._rng.choice(legal_action_indices)
        return self._greedy_index(state_key, legal_action_indices)

    def select_index_greedy(self, state_key: StateKey, legal_action_indices: list[int]) -> int:
        """Deterministic greedy selection (for evaluation); touches no RNG."""
        return self._greedy_index(state_key, legal_action_indices)

    def should_explore(self) -> bool:
        """Draw an exploration coin from the private RNG (for set-valued decisions)."""
        return self._rng.random() < self.current_epsilon

    def random_subset(self, population: list, size: int) -> list:
        """Sample a subset of the given size from the private RNG (reproducible)."""
        return self._rng.sample(population, size)

    # ── learning ──────────────────────────────────────────────────────────────

    def apply_update(self, transition: Transition) -> float:
        """
        Apply one Q-learning or SARSA update for a transition and return the TD error.

        target = reward                                          (terminal)
        target = reward + gamma * max_a' Q(next, a')             (Q-learning)
        target = reward + gamma * Q(next, next_action)           (SARSA)
        """
        row = self.q_row(transition.state_key)
        current_value = row[transition.action_index]

        if transition.done:
            target = transition.reward
        else:
            next_row = self.action_values(transition.next_state_key)
            if self.update_rule == UpdateRule.Q_LEARNING:
                legal = transition.next_legal_action_indices
                bootstrap = max(next_row[action_index] for action_index in legal) if legal else 0.0
            else:
                if transition.next_action_index is None:
                    bootstrap = 0.0
                else:
                    bootstrap = next_row[transition.next_action_index]
            target = transition.reward + self.schedules.gamma * bootstrap

        td_error = target - current_value
        row[transition.action_index] = current_value + self.current_alpha * td_error
        return td_error
