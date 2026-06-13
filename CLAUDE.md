# Volcano Rush

Cooperative/semi-competitive survival board game simulation for 6-8 players. The group is stranded on a volcanic island and must complete missions to build a boat before the volcano erupts.

## Game domain

### Resources (personal hand)
Wood, Stone, Rope. Three types only, held in each player's personal hand. Total deck: 60 cards (20 of each type). Starting hand: 3 cards per player.

### Shared tools (camp)
Knife, Vessel. Tools can be damaged by complications or volcano cards. A damaged tool must be repaired by a Craftsman (costs 1 Stone, takes one round). Only one tool can be under repair at a time.

### Characters
Builder, Fire Starter, Craftsman, Cook, Gatherer, Sailor. Each player gets one visible character card providing passive or active abilities. Role distribution by player count:
- 6 players: all 6 roles used exactly once
- 7 players: all 6 roles + 1 non-Craftsman role repeated at random
- 8 players: all 6 roles + 2 non-Craftsman roles repeated at random

### Missions
13 missions in the catalog, split by `MissionType`: `FIRE`, `FOOD`, `SHELTER`, `BOAT`. Each round, 3 missions are active, drawn from the shuffled mission pool (can include boat missions).

**Resource requirement model:** every resource cost is **per participant**. Each participant individually covers the base mission cost (with their own character's discount applied), any complication card extras, and any pending volcano card extras. Nothing is pooled. The mechanics package splits the mission-resolution flow by responsibility: `requirements.py` (pure cost queries: `compute_per_player_requirements`, `compute_complication_extras`, `compute_volcano_extras`), `affordability.py` (`apply_character_discounts`, `can_afford`), `deductions.py` (`deduct_costs`), and `mission.py` (`resolve_mission` orchestrator).

### Boat scaling
- 6 players: 3 boat parts required (Keel, Hull, Mast)
- 7 players: 4 boat parts required (+ Sail)
- 8 players: 5 boat parts required (+ Fit the Rudder)

### Exhaustion
Any mission participant becomes Exhausted for the following round and cannot participate. The Prepare Food bonus can suppress this (one-time).

### Win / loss
- **Win:** all required boat parts are built before the volcano erupts.
- **Loss:** the Eruption volcano card is drawn (or the volcano tracker reaches its terminal state).

## Simulation engine layout
- `simulation_engine/models/` - enums, dataclasses (missions, complications, volcano cards, state, records)
- `simulation_engine/mechanics/` - resolution logic (`mission.py`, `effects.py`, `exhaustion.py`)
- `simulation_engine/characters/` - one strategy class per file, all implementing `CharacterStrategy` from `base.py`
- `simulation_engine/agents/` - team-level decision functions called from the engine: `feasibility.py` (`AffordLevel` enum, `player_afford_level`, `team_can_afford`), `mission_selection.py` (vote_for_mission, decide_mission_action), `participant_selection.py` (scored participant picking)
- `simulation_engine/engine/` - orchestration package: `game.py` (`run_game`, `run_scenario`), `round.py` (`run_round` and per-branch helpers), `phases.py` (volcano draw, complication draw, mission success, exhaustion, gather). `run_game`/`run_scenario`/`run_round` accept optional `mission_selector` and `participant_selector` callables; when omitted, play is bit-identical to the rule-based agents (this is the hook the RL package uses)
- `simulation_engine/rl/` - tabular reinforcement learning (one-way dependency: imports models/agents/engine, never the reverse): `state_encoding.py` (compact mission/participant state keys), `action_space.py` (semantic mission categories, per-candidate include/exclude), `q_agent.py` (`TabularAgent` with Q-learning and SARSA), `trajectory.py` (semi-MDP transition stitching), `policies.py` (selector wrappers), `training.py` (`train_self_play`), `evaluation.py` (paired evaluation, Wilson interval, McNemar), `persistence.py` (save/load Q-tables)
- `simulation_engine/initialization.py` - deck, player, tool, volcano, mission-pool setup
- `tests/` - pytest suite (engine plus `test_rl_*` for the RL package, including a bit-identical engine-hook gate)
- `notebooks/` - analysis: `math_concepts/` holds the Math Concepts course work (`board_game_simulation.ipynb` entry write-up plus `simulations/`); `data_science/` holds the Data Science course work (`board_game_analysis.ipynb` plus `hypotheses/` and a BGG `helpers/` package); `machine_learning/` holds the Machine Learning course work (`reinforcement_learning.ipynb` entry write-up, `experiments/` notebooks, and a `helpers/` package with the experiment driver and plotting)
- `data/` - `simulations/` and `hypothesis_results/` (exported analysis data), `bgg/` (BoardGameGeek dataset), `rl/` (trained Q-tables, convergence curves, and evaluation summaries)
- `docs/` - human-facing rulebook (characters, missions, game_rules)
