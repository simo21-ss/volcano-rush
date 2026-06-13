"""
Episode trajectory recording and semi-MDP transition stitching.

The agent only acts on some rounds (it votes for a mission and stakes
participants), while shuffle and forfeit rounds advance the game with no agent
action. Each learned decision therefore lives in its own semi-MDP: a decision
transitions to the next decision of the same kind, accumulating any shaping
reward earned in between. The two decision streams (mission and participant)
share one reward stream but never bootstrap across each other's Q-tables.

The recorder collects decisions in temporal order, accrues shaping rewards into
a per-stream accumulator, and on finalize stitches each stream into one-step
transitions, attaching the terminal reward to the last transition of each stream.
"""

from dataclasses import dataclass, field
from typing import Optional

from .state_encoding import StateKey


MISSION_DECISION = "mission"
PARTICIPANT_DECISION = "participant"


@dataclass(frozen = True)
class Transition:
    """One semi-MDP step for a single decision stream."""
    state_key: StateKey
    action_index: int
    reward: float
    next_state_key: Optional[StateKey]
    next_legal_action_indices: Optional[list[int]]
    next_action_index: Optional[int]
    done: bool


@dataclass
class _PendingDecision:
    state_key: StateKey
    action_index: int
    legal_action_indices: list[int]


@dataclass
class TrajectoryRecorder:
    """
    Records decisions and shaping rewards during one self-play game, then emits
    stitched transitions per decision stream.
    """

    _pending: dict[str, Optional[_PendingDecision]] = field(default_factory = dict)
    _reward_since_last: dict[str, float] = field(default_factory = dict)
    _transitions: dict[str, list[Transition]] = field(default_factory = dict)

    def __post_init__(self) -> None:
        for stream in (MISSION_DECISION, PARTICIPANT_DECISION):
            self._pending[stream] = None
            self._reward_since_last[stream] = 0.0
            self._transitions[stream] = []

    def record_decision(
            self,
            decision_type: str,
            state_key: StateKey,
            action_index: int,
            legal_action_indices: list[int],
    ) -> None:
        """
        Record one decision. If a previous decision of the same stream is open,
        close it into a transition leading into this one.
        """
        current = _PendingDecision(state_key, action_index, list(legal_action_indices))
        previous = self._pending[decision_type]
        if previous is not None:
            self._transitions[decision_type].append(
                Transition(
                    state_key = previous.state_key,
                    action_index = previous.action_index,
                    reward = self._reward_since_last[decision_type],
                    next_state_key = current.state_key,
                    next_legal_action_indices = current.legal_action_indices,
                    next_action_index = current.action_index,
                    done = False,
                )
            )
            self._reward_since_last[decision_type] = 0.0
        self._pending[decision_type] = current

    def add_shaping_reward(self, amount: float) -> None:
        """Credit a shaping reward to the open transition of every decision stream."""
        for stream in self._reward_since_last:
            self._reward_since_last[stream] += amount

    def finalize(self, terminal_reward: float) -> dict[str, list[Transition]]:
        """
        Close every open decision into a terminal transition carrying the
        accumulated shaping reward plus the terminal reward, and return the
        per-stream transition lists.
        """
        for stream, previous in self._pending.items():
            if previous is not None:
                self._transitions[stream].append(
                    Transition(
                        state_key = previous.state_key,
                        action_index = previous.action_index,
                        reward = self._reward_since_last[stream] + terminal_reward,
                        next_state_key = None,
                        next_legal_action_indices = None,
                        next_action_index = None,
                        done = True,
                    )
                )
                self._reward_since_last[stream] = 0.0
                self._pending[stream] = None
        return {stream: list(transitions) for stream, transitions in self._transitions.items()}
