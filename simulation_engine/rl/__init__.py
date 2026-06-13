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

__all__ = [
    "StateKey",
    "MissionStateEncoder",
    "ParticipantStateEncoder",
    "bucket_index",
    "next_needed_boat_part",
]
