"""
Orchestrate the end-to-end export: run seeded scenarios, build tables,
write CSVs, emit manifest.json and README.md.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..engine.game import run_scenario
from .tables import SCHEMA, build_tables, compute_game_id
from .writer import write_readme, write_tables


@dataclass
class Scenario:
    player_count: int
    n_games: int
    base_seed: int


def default_scenarios() -> list[Scenario]:
    """Three player counts x 4,000 games each = 12,000 games with seed = deadline date."""
    return [
        Scenario(player_count = player_count, n_games = 4_000, base_seed = 20_260_428)
        for player_count in (6, 7, 8)
    ]


def build_dataset(out_dir: Path, scenarios: list[Scenario] | None = None) -> dict[str, Path]:
    """
    Run every scenario, write per-table CSVs + manifest.json + README.md.

    Returns a dict mapping artifact name (`games`, `manifest`, `readme`, ...)
    to the absolute path of the file that was written.
    """
    resolved_scenarios = default_scenarios() if scenarios is None else scenarios

    all_records = []
    all_game_ids = []
    all_seeds = []
    for scenario in resolved_scenarios:
        records = run_scenario(
            player_count = scenario.player_count,
            n_games = scenario.n_games,
            base_seed = scenario.base_seed,
        )
        for game_index, record in enumerate(records):
            all_records.append(record)
            all_game_ids.append(compute_game_id(scenario.player_count, scenario.base_seed, game_index))
            all_seeds.append(scenario.base_seed + game_index)

    tables = build_tables(all_records, all_game_ids, all_seeds)
    paths = write_tables(tables, out_dir)

    row_counts = { table_name: len(dataframe) for table_name, dataframe in tables.items() }
    readme_path = write_readme(out_dir, row_counts)
    manifest_path = _write_manifest(out_dir, resolved_scenarios, row_counts)

    paths["readme"] = readme_path
    paths["manifest"] = manifest_path
    return paths


def _write_manifest(out_dir: Path, scenarios: list[Scenario], row_counts: dict[str, int]) -> Path:
    schema_with_rows = {
        table_name: { **table_schema, "row_count": row_counts.get(table_name, 0) }
        for table_name, table_schema in SCHEMA.items()
    }

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec = "seconds"),
        "git_sha": _git_sha(),
        "scenarios": [
            {
                "player_count": scenario.player_count,
                "n_games": scenario.n_games,
                "base_seed": scenario.base_seed,
            }
            for scenario in scenarios
        ],
        "tables": schema_with_rows,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent = 2))
    return manifest_path


def _git_sha() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd = Path(__file__).resolve().parent,
            capture_output = True,
            text = True,
            check = False,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None
