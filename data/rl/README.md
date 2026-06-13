# Volcano Rush reinforcement learning artifacts

This folder holds the trained tabular Q-tables and evaluation summaries produced by
`notebooks/machine_learning/helpers/experiment.py` (`train_and_evaluate_all`). The
machine learning notebooks load these artifacts and do not retrain on every run.

The experiment matrix is: player counts {6, 7, 8} x update rules {`q_learning`, `sarsa`}
x ablations {`mission_only`, `participant_only`, `joint`}. Provenance for a regeneration
(episode count, seeds, schedules, reward config, git revision) is recorded in `manifest.json`.

## `manifest.json`

Top-level run parameters and a `cells` list summarising every trained configuration
(player count, update rule, ablation, learned and baseline win rate, McNemar p-value).

## `agent_<decision>_<ablation>_<update_rule>_pc<count>.npz` / `.meta.json`

A trained Q-table for one decision stream. The `.npz` holds two arrays: `keys` (one row
per visited state, each a tuple of small integer features) and `values` (the action-value
row for that state). The `.meta.json` sidecar records the action cardinality, update rule,
schedules, visited-state count, git revision, and the experiment cell it belongs to.
`<decision>` is `mission` or `participant`. Load with
`simulation_engine.rl.load_agent(stem)` (pass the path without a suffix).

## `curves_<ablation>_<update_rule>_pc<count>.json`

Per-run convergence diagnostics recorded in training-episode blocks:

| Key | Description |
| --- | --- |
| `checkpoint_episodes` | Episode index at the end of each diagnostic block. |
| `win_rate_curve` | Self-play win rate within each block (rises as exploration decays). |
| `td_error_curve` | Mean absolute temporal-difference error per block (falls as values settle). |
| `mission_states_curve` | Distinct mission states in the Q-table over time (plateaus below 4608). |
| `participant_states_curve` | Distinct participant states over time (plateaus below 144). |

## `eval_<ablation>_<update_rule>_pc<count>.json`

Paired held-out evaluation of the learned greedy policy against the rule-based baseline on
the same seeds. Holds win counts and rates for both, Wilson 95% intervals, the McNemar test
result (discordant counts, statistic, p-value), and secondary metrics (average rounds,
average boat parts, average volcano cards remaining on wins).
