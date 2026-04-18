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

**Resource requirement model:** mission requirements are **per participant**, not pooled. Each participant must individually hold the per-player cost (after applying their own character's discount). Complication and volcano-card extras are paid once by the group from pooled surplus after per-player costs are deducted. See `simulation_engine/mechanics/mission.py` - `compute_per_player_requirements`, `compute_group_extras`, `check_and_contribute`.

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
- `simulation_engine/agents/` - team-level decision functions called from the engine: `feasibility.py` (affordability helpers), `mission_selection.py` (vote_for_mission, decide_mission_action), `participant_selection.py` (scored participant picking)
- `simulation_engine/engine.py` - `run_game`, `run_scenario` orchestration
- `simulation_engine/initialization.py` - deck, player, tool, volcano, mission-pool setup
- `tests/` - pytest suite
- `notebooks/` - analysis (player-count balance, character balance, resource efficiency)
- `docs/` - human-facing rulebook (characters, missions, game_rules)
