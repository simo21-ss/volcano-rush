"""
Policy wrappers that adapt a TabularAgent into the engine's selector callables.

A policy translates game state into a state key and legal action set, asks its
agent to pick an action (exploring during training, greedy during evaluation),
optionally records the decision into a trajectory, and translates the action
back into the engine's expected return type.

MissionPolicy produces a MissionSelector: (active_player, state) -> Optional[MissionName].
ParticipantPolicy produces a ParticipantSelector: (active_player, mission, state) -> list[Player].
"""

from typing import Optional

from ..models import Player, GameState, Mission, MissionName
from ..agents.feasibility import AffordLevel, player_afford_level
from .state_encoding import MissionStateEncoder, ParticipantStateEncoder
from .action_space import (
    legal_missions, legal_mission_action_indices, decode_mission_action,
    PARTICIPANT_ACTION_EXCLUDE, PARTICIPANT_ACTION_INCLUDE,
)
from .q_agent import TabularAgent
from .trajectory import TrajectoryRecorder, MISSION_DECISION, PARTICIPANT_DECISION


class MissionPolicy:
    """Learned mission-selection policy backed by one TabularAgent."""

    def __init__(self, agent: TabularAgent, encoder: MissionStateEncoder) -> None:
        self.agent = agent
        self.encoder = encoder

    def _choose(self, active_player: Player, state: GameState, explore: bool, recorder: Optional[TrajectoryRecorder]) -> Optional[MissionName]:
        legal = legal_missions(active_player, state)
        if not legal:
            return None

        state_key = self.encoder.encode(active_player, state)
        legal_action_indices = legal_mission_action_indices(active_player, state)

        if explore:
            action_index = self.agent.select_index_training(state_key, legal_action_indices)
        else:
            action_index = self.agent.select_index_greedy(state_key, legal_action_indices)

        if recorder is not None:
            recorder.record_decision(MISSION_DECISION, state_key, action_index, legal_action_indices)

        return decode_mission_action(action_index, legal, state)

    def greedy_selector(self):
        """A MissionSelector that plays greedily and records nothing (for evaluation)."""
        def select(active_player: Player, state: GameState) -> Optional[MissionName]:
            return self._choose(active_player, state, explore = False, recorder = None)
        return select

    def training_selector(self, recorder: TrajectoryRecorder, shaping=None):
        """A MissionSelector that explores and records decisions (for training)."""
        def select(active_player: Player, state: GameState) -> Optional[MissionName]:
            if shaping is not None:
                shaping.on_decision(state, recorder)
            return self._choose(active_player, state, explore = True, recorder = recorder)
        return select


class ParticipantPolicy:
    """Learned participant-selection policy backed by one TabularAgent."""

    def __init__(self, agent: TabularAgent, encoder: ParticipantStateEncoder) -> None:
        self.agent = agent
        self.encoder = encoder

    def _eligible(self, active_player: Player, mission: Mission, state: GameState):
        """Affordable, non-exhausted candidates, as (player_index, candidate, state_key, include_margin)."""
        eligible = []
        for player_index, candidate in enumerate(state.players):
            if candidate.is_exhausted:
                continue
            if player_afford_level(candidate, mission, state) == AffordLevel.CANNOT_AFFORD:
                continue
            state_key = self.encoder.encode(candidate, active_player, mission, state)
            row = self.agent.action_values(state_key)
            include_margin = row[PARTICIPANT_ACTION_INCLUDE] - row[PARTICIPANT_ACTION_EXCLUDE]
            eligible.append((player_index, candidate, state_key, include_margin))
        return eligible

    def _choose(self, active_player: Player, mission: Mission, state: GameState, explore: bool, recorder: Optional[TrajectoryRecorder]) -> list[Player]:
        eligible = self._eligible(active_player, mission, state)
        needed = mission.players_count

        if len(eligible) <= needed:
            chosen_player_indices = {entry[0] for entry in eligible}
        elif explore and self.agent.should_explore():
            sampled = self.agent.random_subset([entry[0] for entry in eligible], needed)
            chosen_player_indices = set(sampled)
        else:
            ranked = sorted(eligible, key = lambda entry: (-entry[3], entry[0]))
            chosen_player_indices = {entry[0] for entry in ranked[:needed]}

        chosen = []
        for player_index, candidate, state_key, _ in eligible:
            is_chosen = player_index in chosen_player_indices
            if recorder is not None:
                action_index = PARTICIPANT_ACTION_INCLUDE if is_chosen else PARTICIPANT_ACTION_EXCLUDE
                recorder.record_decision(
                    PARTICIPANT_DECISION, state_key, action_index,
                    [PARTICIPANT_ACTION_EXCLUDE, PARTICIPANT_ACTION_INCLUDE],
                )
            if is_chosen:
                chosen.append(candidate)
        return chosen

    def greedy_selector(self):
        """A ParticipantSelector that ranks greedily and records nothing (for evaluation)."""
        def select(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
            return self._choose(active_player, mission, state, explore = False, recorder = None)
        return select

    def training_selector(self, recorder: TrajectoryRecorder, shaping=None):
        """A ParticipantSelector that explores and records decisions (for training)."""
        def select(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
            if shaping is not None:
                shaping.on_decision(state, recorder)
            return self._choose(active_player, mission, state, explore = True, recorder = recorder)
        return select
