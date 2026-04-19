"""CLI entry point: `python -m simulation_engine.export [--out-dir DIR]`."""

from __future__ import annotations

import argparse
from pathlib import Path

from .runner import build_dataset


_DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "simulations"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog = "python -m simulation_engine.export",
        description = "Run the default simulation scenarios and write CSVs + manifest + README.",
    )
    parser.add_argument(
        "--out-dir",
        type = Path,
        default = _DEFAULT_OUT_DIR,
        help = f"Output directory for the CSVs (default: {_DEFAULT_OUT_DIR}).",
    )
    args = parser.parse_args()

    paths = build_dataset(out_dir = args.out_dir)
    print(f"Wrote {len(paths)} artifacts to {args.out_dir}:")
    for name, path in paths.items():
        print(f"  {name}: {path.name}")


if __name__ == "__main__":
    main()
