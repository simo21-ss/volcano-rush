"""
Self-play training loop.

Each episode is one seeded game played with the learned selectors injected via
the engine hook. The agent's exploration uses its own private RNG, while the
game's dynamics are seeded from the global random stream exactly as run_scenario
does, so the dynamics are reproducible and independent of the exploration noise.

Reward shaping is injected at decision points by a ShapingTracker keyed on the
round number, so a small per-round step penalty and a per-boat-part bonus are
each counted once per round regardless of how many selectors fire that round.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from ..engine.game import run_game
from ..models import GameOutcome
from .state_encoding import MissionStateEncoder, ParticipantStateEncoder
from .action_space import MISSION_ACTION_CARDINALITY, PARTICIPANT_ACTION_CARDINALITY
from .q_agent import TabularAgent, Schedules, UpdateRule
from .trajectory import TrajectoryRecorder, MISSION_DECISION, PARTICIPANT_DECISION
from .policies import MissionPolicy, ParticipantPolicy


@dataclass
class RewardConfig:
    """Terminal rewards and optional shaping coefficients."""
    win_reward: float = 1.0
    loss_reward: float = -1.0
    boat_part_reward: float = 0.1
    step_penalty: float = 0.002
    use_shaping: bool = True


@dataclass
class TrainingConfig:
    player_count: int
    n_episodes: int
    base_seed: int
    schedules: Schedules = field(default_factory = Schedules)
    reward_config: RewardConfig = field(default_factory = RewardConfig)
    update_rule: UpdateRule = UpdateRule.Q_LEARNING
    learn_mission: bool = True
    learn_participant: bool = True
    exploration_seed: int = 0
    mission_encoder: MissionStateEncoder = field(default_factory = MissionStateEncoder)
    participant_encoder: ParticipantStateEncoder = field(default_factory = ParticipantStateEncoder)
    checkpoint_interval: Optional[int] = None   # episodes per diagnostic block; defaults to n_episodes // 100


@dataclass
class TrainingResult:
    mission_agent: Optional[TabularAgent]
    participant_agent: Optional[TabularAgent]
    checkpoint_episodes: list = field(default_factory = list)
    win_rate_curve: list = field(default_factory = list)
    td_error_curve: list = field(default_factory = list)
    mission_states_curve: list = field(default_factory = list)
    participant_states_curve: list = field(default_factory = list)


class ShapingTracker:
    """Injects per-round shaping rewards into a recorder, once per round."""

    def __init__(self, reward_config: RewardConfig) -> None:
        self.reward_config = reward_config
        self.last_round = None
        self.previous_boat_count = 0

    def on_decision(self, state, recorder: TrajectoryRecorder) -> None:
        if not self.reward_config.use_shaping:
            return
        if state.round == self.last_round:
            return
        self.last_round = state.round
        boat_count = len(state.boat_parts_built)
        boat_delta = boat_count - self.previous_boat_count
        if boat_delta > 0:
            recorder.add_shaping_reward(self.reward_config.boat_part_reward * boat_delta)
        self.previous_boat_count = boat_count
        recorder.add_shaping_reward(-self.reward_config.step_penalty)

    def finalize(self, final_boat_parts_built: int, recorder: TrajectoryRecorder) -> None:
        if not self.reward_config.use_shaping:
            return
        boat_delta = final_boat_parts_built - self.previous_boat_count
        if boat_delta > 0:
            recorder.add_shaping_reward(self.reward_config.boat_part_reward * boat_delta)


def train_self_play(config: TrainingConfig) -> TrainingResult:
    """Train mission and/or participant agents by self-play and return diagnostics."""
    if not config.learn_mission and not config.learn_participant:
        raise ValueError("At least one of learn_mission or learn_participant must be True.")

    mission_agent = None
    mission_policy = None
    if config.learn_mission:
        mission_agent = TabularAgent(
            MISSION_ACTION_CARDINALITY, config.schedules, config.update_rule,
            exploration_seed = config.exploration_seed,
        )
        mission_policy = MissionPolicy(mission_agent, config.mission_encoder)

    participant_agent = None
    participant_policy = None
    if config.learn_participant:
        participant_agent = TabularAgent(
            PARTICIPANT_ACTION_CARDINALITY, config.schedules, config.update_rule,
            exploration_seed = config.exploration_seed + 1,
        )
        participant_policy = ParticipantPolicy(participant_agent, config.participant_encoder)

    checkpoint_interval = config.checkpoint_interval or max(1, config.n_episodes // 100)
    result = TrainingResult(mission_agent = mission_agent, participant_agent = participant_agent)

    block_wins = 0
    block_games = 0
    block_td_total = 0.0
    block_td_count = 0

    for episode_index in range(config.n_episodes):
        if mission_agent is not None:
            mission_agent.set_episode(episode_index)
        if participant_agent is not None:
            participant_agent.set_episode(episode_index)

        random.seed(config.base_seed + episode_index)
        recorder = TrajectoryRecorder()
        shaping = ShapingTracker(config.reward_config)

        mission_selector = mission_policy.training_selector(recorder, shaping) if mission_policy is not None else None
        participant_selector = participant_policy.training_selector(recorder, shaping) if participant_policy is not None else None

        record = run_game(
            player_count = config.player_count,
            mission_selector = mission_selector,
            participant_selector = participant_selector,
        )

        shaping.finalize(record.boat_parts_built, recorder)
        terminal_reward = (
            config.reward_config.win_reward if record.outcome == GameOutcome.WIN
            else config.reward_config.loss_reward
        )
        transitions = recorder.finalize(terminal_reward)

        for stream, agent in ((MISSION_DECISION, mission_agent), (PARTICIPANT_DECISION, participant_agent)):
            if agent is None:
                continue
            for transition in transitions[stream]:
                td_error = agent.apply_update(transition)
                block_td_total += abs(td_error)
                block_td_count += 1

        block_wins += 1 if record.outcome == GameOutcome.WIN else 0
        block_games += 1

        is_last_episode = episode_index == config.n_episodes - 1
        if block_games == checkpoint_interval or is_last_episode:
            result.checkpoint_episodes.append(episode_index + 1)
            result.win_rate_curve.append(block_wins / block_games)
            result.td_error_curve.append(block_td_total / block_td_count if block_td_count else 0.0)
            result.mission_states_curve.append(mission_agent.visited_state_count if mission_agent else 0)
            result.participant_states_curve.append(participant_agent.visited_state_count if participant_agent else 0)
            block_wins = 0
            block_games = 0
            block_td_total = 0.0
            block_td_count = 0

    return result
