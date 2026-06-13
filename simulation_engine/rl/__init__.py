"""
Tabular reinforcement learning for Volcano Rush mission and participant choices.

This package learns two of the engine's per-round decisions from self-play and
exposes them as the MissionSelector / ParticipantSelector callables the engine
hook accepts. It depends on models/, agents/, and engine/; the engine never
depends on this package, keeping the default game free of RL concerns.
"""

from .state_encoding import (
    StateKey,
    MissionStateEncoder,
    ParticipantStateEncoder,
    bucket_index,
    next_needed_boat_part,
)
from .action_space import (
    MISSION_ACTION_CARDINALITY,
    PARTICIPANT_ACTION_CARDINALITY,
    PARTICIPANT_ACTION_EXCLUDE,
    PARTICIPANT_ACTION_INCLUDE,
    legal_missions,
    encode_mission_action,
    legal_mission_action_indices,
    decode_mission_action,
)

__all__ = [
    "StateKey",
    "MissionStateEncoder",
    "ParticipantStateEncoder",
    "bucket_index",
    "next_needed_boat_part",
    "MISSION_ACTION_CARDINALITY",
    "PARTICIPANT_ACTION_CARDINALITY",
    "PARTICIPANT_ACTION_EXCLUDE",
    "PARTICIPANT_ACTION_INCLUDE",
    "legal_missions",
    "encode_mission_action",
    "legal_mission_action_indices",
    "decode_mission_action",
]
