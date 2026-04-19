# Volcano Rush simulation dataset

This folder contains CSVs produced by `python -m simulation_engine.export`.
The provenance of a given run (seed, scenarios, git sha, timestamp) is recorded in `manifest.json`.

All tables are joinable on `game_id`.

## `games.csv`

- **Grain**: one row per simulated game
- **Primary key**: `game_id`
- **Rows**: 12,000

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | string | Stable hash of player_count + base_seed + game_index. Joins to all other tables. |
| `seed` | int | RNG seed used for this game (base_seed + game_index). |
| `player_count` | int | Number of players (6, 7, or 8). Drives boat parts required and character distribution. |
| `outcome` | string | 'win' if all required boat parts built before eruption, else 'loss'. |
| `rounds_played` | int | Total rounds played before win, loss, or timeout. |
| `boat_parts_built` | int | Number of boat parts completed when the game ended. |
| `boat_parts_required` | int | Boat parts needed to win at this player count (3 / 4 / 5). |
| `volcano_cards_remaining` | int | Volcano deck size at game end. Higher = more time was left when the game ended. |
| `mission_failures_any_extra` | int | Mission failures caused by a shortage of any-type resources demanded by a complication card. |

## `game_characters.csv`

- **Grain**: one row per (game, character) pairing
- **Primary key**: `game_id, character`
- **Rows**: 84,000

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | string | Foreign key to games.game_id. |
| `character` | string | Character role name (e.g. BUILDER, SAILOR). Enum name, not value. |
| `final_score` | int | Personal score at game end. Awarded by mission participation and Cook food bonuses. |
| `won` | bool | True if the game's outcome was a win. Duplicated here for convenience so character-centric analysis does not need to join games.csv. |

## `game_resources.csv`

- **Grain**: one row per (game, resource) pairing (long format)
- **Primary key**: `game_id, resource`
- **Rows**: 36,000

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | string | Foreign key to games.game_id. |
| `resource` | string | Resource type. One of WOOD, STONE, ROPE. |
| `consumed` | int | Total units of this resource spent on successful missions during the game. |
| `mission_failures` | int | Count of missions that failed due to insufficient supply of this resource type (base + complication + volcano cost). |

## `game_tools.csv`

- **Grain**: one row per (game, tool) pairing (long format)
- **Primary key**: `game_id, tool`
- **Rows**: 24,000

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | string | Foreign key to games.game_id. |
| `tool` | string | Tool type. One of KNIFE, VESSEL. |
| `repairs` | int | Number of times this tool was repaired by a Craftsman during the game. |
| `mission_failures_damaged` | int | Count of missions that failed because this tool was damaged and unavailable. |

## `character_contributions.csv`

- **Grain**: one row per (game, character) pairing, win games only
- **Primary key**: `game_id, character`
- **Rows**: 34,122

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | string | Foreign key to games.game_id. Only games with outcome == 'win' appear in this table. |
| `character` | string | Character role name. Enum name, not value. |
| `missions_participated` | int | Count of missions this character participated in during the game. |
| `boat_missions_participated` | int | Subset of missions_participated that were boat-building missions. |
| `tools_repaired` | int | Count of tool repairs performed by this character (Craftsman-only contribution). |
| `lesser_evil_uses` | int | Count of lesser-evil trade-off decisions invoked by this character to dodge a complication. |
| `requirement_discounts_used` | int | Count of times this character's passive or active ability reduced a mission's resource requirement. |
