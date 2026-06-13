"""
Persist and reload trained Q-tables.

A trained agent is saved as a NumPy .npz (one integer matrix of state keys and
one float matrix of action values) plus a JSON sidecar holding the schedules,
update rule, action cardinality, and free-form metadata (encoder parameters,
player count, episode count, git revision). Notebooks load the saved tables and
never retrain on every run.
"""

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import numpy as np

from .q_agent import TabularAgent, Schedules, UpdateRule


def git_revision() -> Optional[str]:
    """Return the current git commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output = True,
            text = True,
            check = True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _values_path(path: Path) -> Path:
    return path.with_suffix(".npz")


def _meta_path(path: Path) -> Path:
    return path.with_suffix(".meta.json")


def save_agent(agent: TabularAgent, path, metadata: Optional[dict] = None) -> Path:
    """
    Save an agent's Q-table to <path>.npz and its metadata to <path>.meta.json.

    Returns the .npz path. The path argument is treated as a stem; any suffix is
    replaced.
    """
    path = Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)

    items = agent.table_items()
    if items:
        keys_array = np.array([list(state_key) for state_key, _ in items], dtype = int)
        values_array = np.array([row for _, row in items], dtype = float)
    else:
        keys_array = np.zeros((0, 0), dtype = int)
        values_array = np.zeros((0, agent.action_cardinality), dtype = float)

    np.savez(_values_path(path), keys = keys_array, values = values_array)

    meta = {
        "action_cardinality": agent.action_cardinality,
        "update_rule": agent.update_rule.value,
        "schedules": asdict(agent.schedules),
        "visited_state_count": agent.visited_state_count,
        "git_revision": git_revision(),
    }
    if metadata:
        meta.update(metadata)
    _meta_path(path).write_text(json.dumps(meta, indent = 2))

    return _values_path(path)


def load_metadata(path) -> dict:
    """Load the JSON sidecar metadata for a saved agent."""
    return json.loads(_meta_path(Path(path)).read_text())


def load_agent(path, exploration_seed: int = 0) -> TabularAgent:
    """Reconstruct a TabularAgent from a saved Q-table and its metadata sidecar."""
    path = Path(path)
    meta = load_metadata(path)

    schedules = Schedules(**meta["schedules"])
    update_rule = UpdateRule(meta["update_rule"])
    agent = TabularAgent(
        action_cardinality = meta["action_cardinality"],
        schedules = schedules,
        update_rule = update_rule,
        exploration_seed = exploration_seed,
    )

    with np.load(_values_path(path)) as stored:
        keys_array = stored["keys"]
        values_array = stored["values"]

    for row_index in range(keys_array.shape[0]):
        state_key = tuple(int(value) for value in keys_array[row_index])
        agent.q_row(state_key)[:] = values_array[row_index]

    return agent
