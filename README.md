# Math Concepts for Developers - Course Project

Volcano Rush - Board Game

## Setup

```bash
conda env create -f environment.yml
conda activate math-course-project
jupyter notebook
```

Notebooks are in the `notebooks/` directory.

## Data

The `data/` folder holds the two independent data sources used in the analysis:

- `data/simulations/` - CSVs produced by the simulation engine. Regenerate with:
  ```bash
  python -m simulation_engine.export
  ```
  Schema and per-column descriptions are in `data/simulations/README.md`; run provenance (seed, git sha, timestamp) is in `data/simulations/manifest.json`.

- `data/bgg/` - BoardGameGeek board games dataset from Kaggle. Not tracked in git (the full dataset is ~650 MB and one file exceeds GitHub's per-file limit). Fetch with:
  ```bash
  kaggle datasets download -d threnjen/board-games-database-from-boardgamegeek -p data/bgg/ --unzip
  ```
  Requires a Kaggle API token at `~/.kaggle/kaggle.json` (free signup at kaggle.com).
