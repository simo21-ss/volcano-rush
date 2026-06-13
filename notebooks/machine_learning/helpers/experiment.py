"""
Experiment driver for the reinforcement learning study.

Defines the full experiment matrix - player counts {6, 7, 8} x update rules
{Q-learning, SARSA} x ablations {mission-only, participant-only, joint} - and
trains, evaluates, and persists every cell to data/rl/. The notebooks import
this module and load the persisted artifacts rather than retraining on every run.

Run standalone to regenerate all artifacts:

    python -m notebooks.machine_learning.helpers.experiment

or from a notebook:

    import helpers.experiment as experiment
    experiment.train_and_evaluate_all()
"""

import json
from dataclasses import asdict
from pathlib import Path

from simulation_engine.engine.game import run_scenario
from simulation_engine.models import GameOutcome
from simulation_engine.rl.q_agent import Schedules, UpdateRule
from simulation_engine.rl.training import TrainingConfig, RewardConfig, train_self_play
from simulation_engine.rl.policies import MissionPolicy, ParticipantPolicy
from simulation_engine.rl.evaluation import EvaluationResult
from simulation_engine.rl.persistence import save_agent, git_revision


PLAYER_COUNTS = (6, 7, 8)
UPDATE_RULES = (UpdateRule.Q_LEARNING, UpdateRule.SARSA)
ABLATIONS = {
    "mission_only": {"learn_mission": True, "learn_participant": False},
    "participant_only": {"learn_mission": False, "learn_participant": True},
    "joint": {"learn_mission": True, "learn_participant": True},
}

DEFAULT_EPISODES = 30_000
TRAIN_BASE_SEED = 1_000
EVAL_BASE_SEED = 600_000
DEFAULT_EVAL_GAMES = 4_000

DATA_DIRECTORY = Path(__file__).resolve().parents[3] / "data" / "rl"


def _exploration_seed(player_count: int, update_rule: UpdateRule, ablation_name: str) -> int:
    """A distinct, reproducible exploration seed per experiment cell."""
    rule_offset = 0 if update_rule == UpdateRule.Q_LEARNING else 1
    ablation_offset = list(ABLATIONS).index(ablation_name)
    return 10_000 + player_count * 100 + rule_offset * 10 + ablation_offset


def agent_stem(data_directory: Path, decision: str, ablation_name: str, update_rule: UpdateRule, player_count: int) -> Path:
    return data_directory / f"agent_{decision}_{ablation_name}_{update_rule.value}_pc{player_count}"


def curves_path(data_directory: Path, ablation_name: str, update_rule: UpdateRule, player_count: int) -> Path:
    return data_directory / f"curves_{ablation_name}_{update_rule.value}_pc{player_count}.json"


def evaluation_path(data_directory: Path, ablation_name: str, update_rule: UpdateRule, player_count: int) -> Path:
    return data_directory / f"eval_{ablation_name}_{update_rule.value}_pc{player_count}.json"


def _secondary_metrics(records: list) -> dict:
    n_games = len(records)
    wins = [record for record in records if record.outcome == GameOutcome.WIN]
    average_rounds = sum(record.rounds_played for record in records) / n_games
    average_boat_parts = sum(record.boat_parts_built for record in records) / n_games
    average_volcano_remaining_on_win = (
        sum(record.volcano_cards_remaining for record in wins) / len(wins) if wins else 0.0
    )
    return {
        "average_rounds": average_rounds,
        "average_boat_parts": average_boat_parts,
        "average_volcano_remaining_on_win": average_volcano_remaining_on_win,
    }


def _evaluation_summary(evaluation: EvaluationResult, ablation_name: str, update_rule: UpdateRule) -> dict:
    rl_interval = evaluation.rl_win_interval()
    baseline_interval = evaluation.baseline_win_interval()
    mcnemar = evaluation.mcnemar()
    return {
        "ablation": ablation_name,
        "update_rule": update_rule.value,
        "player_count": evaluation.player_count,
        "n_games": evaluation.n_games,
        "rl_wins": evaluation.rl_wins,
        "baseline_wins": evaluation.baseline_wins,
        "rl_win_rate": evaluation.rl_win_rate,
        "baseline_win_rate": evaluation.baseline_win_rate,
        "rl_win_interval": asdict(rl_interval),
        "baseline_win_interval": asdict(baseline_interval),
        "mcnemar": asdict(mcnemar),
        "rl_secondary": _secondary_metrics(evaluation.rl_records),
        "baseline_secondary": _secondary_metrics(evaluation.baseline_records),
    }


def _save_curves(result, path: Path) -> None:
    path.write_text(json.dumps({
        "checkpoint_episodes": result.checkpoint_episodes,
        "win_rate_curve": result.win_rate_curve,
        "td_error_curve": result.td_error_curve,
        "mission_states_curve": result.mission_states_curve,
        "participant_states_curve": result.participant_states_curve,
    }, indent = 2))


def train_and_evaluate_all(
        data_directory: Path = DATA_DIRECTORY,
        n_episodes: int = DEFAULT_EPISODES,
        eval_games: int = DEFAULT_EVAL_GAMES,
        progress = print,
) -> dict:
    """Train, evaluate, and persist every experiment cell. Returns the manifest."""
    data_directory.mkdir(parents = True, exist_ok = True)
    schedules = Schedules(epsilon_decay_episodes = int(n_episodes * 0.7))
    reward_config = RewardConfig()

    manifest = {
        "n_episodes": n_episodes,
        "eval_games": eval_games,
        "train_base_seed": TRAIN_BASE_SEED,
        "eval_base_seed": EVAL_BASE_SEED,
        "schedules": asdict(schedules),
        "reward_config": asdict(reward_config),
        "git_revision": git_revision(),
        "player_counts": list(PLAYER_COUNTS),
        "update_rules": [rule.value for rule in UPDATE_RULES],
        "ablations": list(ABLATIONS),
        "cells": [],
    }

    for player_count in PLAYER_COUNTS:
        # The baseline is identical across rules and ablations, so compute it once per count.
        progress(f"player_count {player_count}: baseline evaluation ({eval_games} games)")
        baseline_records = run_scenario(player_count = player_count, n_games = eval_games, base_seed = EVAL_BASE_SEED)

        for update_rule in UPDATE_RULES:
            for ablation_name, flags in ABLATIONS.items():
                progress(f"player_count {player_count} | {update_rule.value} | {ablation_name}: training {n_episodes} episodes")
                config = TrainingConfig(
                    player_count = player_count,
                    n_episodes = n_episodes,
                    base_seed = TRAIN_BASE_SEED,
                    schedules = schedules,
                    reward_config = reward_config,
                    update_rule = update_rule,
                    exploration_seed = _exploration_seed(player_count, update_rule, ablation_name),
                    **flags,
                )
                result = train_self_play(config)

                metadata_common = {
                    "ablation": ablation_name,
                    "update_rule": update_rule.value,
                    "player_count": player_count,
                    "n_episodes": n_episodes,
                    "train_base_seed": TRAIN_BASE_SEED,
                    "exploration_seed": config.exploration_seed,
                }
                if result.mission_agent is not None:
                    save_agent(
                        result.mission_agent,
                        agent_stem(data_directory, "mission", ablation_name, update_rule, player_count),
                        metadata = {**metadata_common, "decision": "mission"},
                    )
                if result.participant_agent is not None:
                    save_agent(
                        result.participant_agent,
                        agent_stem(data_directory, "participant", ablation_name, update_rule, player_count),
                        metadata = {**metadata_common, "decision": "participant"},
                    )
                _save_curves(result, curves_path(data_directory, ablation_name, update_rule, player_count))

                # Evaluate the learned greedy policy on held-out seeds, paired with the shared baseline.
                mission_selector = (
                    MissionPolicy(result.mission_agent, config.mission_encoder).greedy_selector()
                    if result.mission_agent is not None else None
                )
                participant_selector = (
                    ParticipantPolicy(result.participant_agent, config.participant_encoder).greedy_selector()
                    if result.participant_agent is not None else None
                )
                rl_records = run_scenario(
                    player_count = player_count,
                    n_games = eval_games,
                    base_seed = EVAL_BASE_SEED,
                    mission_selector = mission_selector,
                    participant_selector = participant_selector,
                )
                evaluation = EvaluationResult(
                    player_count = player_count,
                    n_games = eval_games,
                    rl_records = rl_records,
                    baseline_records = baseline_records,
                )
                summary = _evaluation_summary(evaluation, ablation_name, update_rule)
                evaluation_path(data_directory, ablation_name, update_rule, player_count).write_text(json.dumps(summary, indent = 2))

                manifest["cells"].append({
                    "player_count": player_count,
                    "update_rule": update_rule.value,
                    "ablation": ablation_name,
                    "rl_win_rate": summary["rl_win_rate"],
                    "baseline_win_rate": summary["baseline_win_rate"],
                    "mcnemar_p_value": summary["mcnemar"]["p_value"],
                })
                progress(
                    f"    rl {summary['rl_win_rate']:.3f} vs baseline {summary['baseline_win_rate']:.3f} "
                    f"(McNemar p={summary['mcnemar']['p_value']:.3f})"
                )

    (data_directory / "manifest.json").write_text(json.dumps(manifest, indent = 2))
    progress(f"done: wrote artifacts to {data_directory}")
    return manifest


if __name__ == "__main__":
    train_and_evaluate_all()
