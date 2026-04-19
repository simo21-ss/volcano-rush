"""
Write the export tables to disk as CSVs, plus a human-readable README.md
rendered from the same SCHEMA that `tables.py` exposes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .tables import SCHEMA


def write_tables(tables: dict[str, pd.DataFrame], out_dir: Path) -> dict[str, Path]:
    """
    Write every table in `tables` to `out_dir` as `<table_name>.csv`.

    Column order follows SCHEMA. Enum-name serialization is handled by
    `tables.py` before the values reach us here.
    """
    out_dir.mkdir(parents = True, exist_ok = True)
    written = {}
    for table_name, dataframe in tables.items():
        output_path = out_dir / f"{table_name}.csv"
        dataframe.to_csv(output_path, index = False)
        written[table_name] = output_path
    return written


def write_readme(out_dir: Path, row_counts: dict[str, int]) -> Path:
    """Render `out_dir/README.md` from SCHEMA and measured row counts."""
    out_dir.mkdir(parents = True, exist_ok = True)
    output_path = out_dir / "README.md"
    output_path.write_text(_render_readme(row_counts))
    return output_path


def _render_readme(row_counts: dict[str, int]) -> str:
    lines = [
        "# Volcano Rush simulation dataset",
        "",
        "This folder contains CSVs produced by `python -m simulation_engine.export`.",
        "The provenance of a given run (seed, scenarios, git sha, timestamp) is recorded in `manifest.json`.",
        "",
        "All tables are joinable on `game_id`.",
        "",
    ]
    for table_name, table_schema in SCHEMA.items():
        lines.append(f"## `{table_name}.csv`")
        lines.append("")
        lines.append(f"- **Grain**: {table_schema['grain']}")
        lines.append(f"- **Primary key**: `{', '.join(table_schema['primary_key'])}`")
        lines.append(f"- **Rows**: {row_counts.get(table_name, 0):,}")
        lines.append("")
        lines.append("| Column | Type | Description |")
        lines.append("| --- | --- | --- |")
        for column in table_schema["columns"]:
            lines.append(f"| `{column['name']}` | {column['dtype']} | {column['description']} |")
        lines.append("")
    return "\n".join(lines)
