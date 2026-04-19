"""
Row builders and schema for the simulation export.

`SCHEMA` is the single source of truth for table grain, primary keys, column
order, dtypes, and human-readable descriptions. `writer.py` uses it to order
CSV columns; `runner.py` embeds it in manifest.json; `writer.py` also renders
the sidecar README.md from it.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd

from ..models import GameOutcome, GameRecord, Resource, Tool

SCHEMA: dict[str, dict[str, Any]] = {
    "games": {
        "grain": "one row per simulated game",
        "primary_key": ["game_id"],
        "columns": [
            { "name": "game_id", "dtype": "string", "description": "Stable hash of player_count + base_seed + game_index. Joins to all other tables." },
            { "name": "seed", "dtype": "int", "description": "RNG seed used for this game (base_seed + game_index)." },
            { "name": "player_count", "dtype": "int", "description": "Number of players (6, 7, or 8). Drives boat parts required and character distribution." },
            { "name": "outcome", "dtype": "string", "description": "'win' if all required boat parts built before eruption, else 'loss'." },
            { "name": "rounds_played", "dtype": "int", "description": "Total rounds played before win, loss, or timeout." },
            { "name": "boat_parts_built", "dtype": "int", "description": "Number of boat parts completed when the game ended." },
            { "name": "boat_parts_required", "dtype": "int", "description": "Boat parts needed to win at this player count (3 / 4 / 5)." },
            { "name": "volcano_cards_remaining", "dtype": "int", "description": "Volcano deck size at game end. Higher = more time was left when the game ended." },
            { "name": "mission_failures_any_extra", "dtype": "int", "description": "Mission failures caused by a shortage of any-type resources demanded by a complication card." },
        ],
    },
    "game_characters": {
        "grain": "one row per (game, character) pairing",
        "primary_key": ["game_id", "character"],
        "columns": [
            { "name": "game_id", "dtype": "string", "description": "Foreign key to games.game_id." },
            { "name": "character", "dtype": "string", "description": "Character role name (e.g. BUILDER, SAILOR). Enum name, not value." },
            { "name": "final_score", "dtype": "int", "description": "Personal score at game end. Awarded by mission participation and Cook food bonuses." },
            { "name": "won", "dtype": "bool", "description": "True if the game's outcome was a win. Duplicated here for convenience so character-centric analysis does not need to join games.csv." },
        ],
    },
    "game_resources": {
        "grain": "one row per (game, resource) pairing (long format)",
        "primary_key": ["game_id", "resource"],
        "columns": [
            { "name": "game_id", "dtype": "string", "description": "Foreign key to games.game_id." },
            { "name": "resource", "dtype": "string", "description": "Resource type. One of WOOD, STONE, ROPE." },
            { "name": "consumed", "dtype": "int", "description": "Total units of this resource spent on successful missions during the game." },
            { "name": "mission_failures", "dtype": "int", "description": "Count of missions that failed due to insufficient supply of this resource type (base + complication + volcano cost)." },
        ],
    },
    "game_tools": {
        "grain": "one row per (game, tool) pairing (long format)",
        "primary_key": ["game_id", "tool"],
        "columns": [
            { "name": "game_id", "dtype": "string", "description": "Foreign key to games.game_id." },
            { "name": "tool", "dtype": "string", "description": "Tool type. One of KNIFE, VESSEL." },
            { "name": "repairs", "dtype": "int", "description": "Number of times this tool was repaired by a Craftsman during the game." },
            { "name": "mission_failures_damaged", "dtype": "int", "description": "Count of missions that failed because this tool was damaged and unavailable." },
        ],
    },
    "character_contributions": {
        "grain": "one row per (game, character) pairing, win games only",
        "primary_key": ["game_id", "character"],
        "columns": [
            { "name": "game_id", "dtype": "string", "description": "Foreign key to games.game_id. Only games with outcome == 'win' appear in this table." },
            { "name": "character", "dtype": "string", "description": "Character role name. Enum name, not value." },
            { "name": "missions_participated", "dtype": "int", "description": "Count of missions this character participated in during the game." },
            { "name": "boat_missions_participated", "dtype": "int", "description": "Subset of missions_participated that were boat-building missions." },
            { "name": "tools_repaired", "dtype": "int", "description": "Count of tool repairs performed by this character (Craftsman-only contribution)." },
            { "name": "lesser_evil_uses", "dtype": "int", "description": "Count of lesser-evil trade-off decisions invoked by this character to dodge a complication." },
            { "name": "requirement_discounts_used", "dtype": "int", "description": "Count of times this character's passive or active ability reduced a mission's resource requirement." },
        ],
    },
}


def compute_game_id(player_count: int, base_seed: int, game_index: int) -> str:
    """Stable short hash of the coordinates that uniquely identify a simulated game."""
    key = f"{player_count}:{base_seed}:{game_index}"
    return hashlib.blake2b(key.encode(), digest_size = 8).hexdigest()


def _games_rows(records: list[tuple[GameRecord, str, int]]) -> list[dict]:
    rows = []
    for record, game_id, seed in records:
        rows.append({
            "game_id": game_id,
            "seed": seed,
            "player_count": record.player_count,
            "outcome": record.outcome.value,
            "rounds_played": record.rounds_played,
            "boat_parts_built": record.boat_parts_built,
            "boat_parts_required": record.boat_parts_required,
            "volcano_cards_remaining": record.volcano_cards_remaining,
            "mission_failures_any_extra": record.mission_failures_any_extra,
        })
    return rows


def _game_characters_rows(records: list[tuple[GameRecord, str, int]]) -> list[dict]:
    rows = []
    for record, game_id, _seed in records:
        won = record.outcome == GameOutcome.WIN
        for character in record.characters:
            rows.append({
                "game_id": game_id,
                "character": character.name,
                "final_score": record.final_scores[character],
                "won": won,
            })
    return rows


def _game_resources_rows(records: list[tuple[GameRecord, str, int]]) -> list[dict]:
    rows = []
    for record, game_id, _seed in records:
        for resource in Resource:
            rows.append({
                "game_id": game_id,
                "resource": resource.name,
                "consumed": record.resources_consumed.get(resource, 0),
                "mission_failures": record.mission_failures_by_resource.get(resource, 0),
            })
    return rows


def _game_tools_rows(records: list[tuple[GameRecord, str, int]]) -> list[dict]:
    rows = []
    for record, game_id, _seed in records:
        for tool in Tool:
            rows.append({
                "game_id": game_id,
                "tool": tool.name,
                "repairs": record.tool_repairs.get(tool, 0),
                "mission_failures_damaged": record.mission_failures_tool_damaged.get(tool, 0),
            })
    return rows


def _character_contributions_rows(records: list[tuple[GameRecord, str, int]]) -> list[dict]:
    rows = []
    for record, game_id, _seed in records:
        if record.outcome != GameOutcome.WIN:
            continue
        for character, contribution in record.contributions.items():
            rows.append({
                "game_id": game_id,
                "character": character.name,
                "missions_participated": contribution.missions_participated,
                "boat_missions_participated": contribution.boat_missions_participated,
                "tools_repaired": contribution.tools_repaired,
                "lesser_evil_uses": contribution.lesser_evil_uses,
                "requirement_discounts_used": contribution.requirement_discounts_used,
            })
    return rows


_ROW_BUILDERS = {
    "games": _games_rows,
    "game_characters": _game_characters_rows,
    "game_resources": _game_resources_rows,
    "game_tools": _game_tools_rows,
    "character_contributions": _character_contributions_rows,
}


def build_tables(records: list[GameRecord], game_ids: list[str], seeds: list[int]) -> dict[str, pd.DataFrame]:
    """
    Build one DataFrame per table from a list of GameRecord.

    `game_ids` and `seeds` are positional sidecars: `game_ids[i]` and `seeds[i]`
    correspond to `records[i]`. This keeps tables.py free of seed-arithmetic
    so the caller (runner.py) stays in charge of scenario composition.
    """
    if not (len(records) == len(game_ids) == len(seeds)):
        raise ValueError("records, game_ids, and seeds must be the same length")

    paired = list(zip(records, game_ids, seeds))
    tables = { }
    for table_name, builder in _ROW_BUILDERS.items():
        rows = builder(paired)
        columns = [column["name"] for column in SCHEMA[table_name]["columns"]]
        dataframe = pd.DataFrame(rows, columns = columns)
        tables[table_name] = dataframe
    return tables
