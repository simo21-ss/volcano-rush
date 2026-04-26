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

- `data/bgg/` - the two BoardGameGeek tables used in the analysis (`games.csv`, `mechanics.csv`) are committed directly so the project is self-contained. Source: Kaggle dataset *Board Games Database from BoardGameGeek* by threnjen, downloaded 2026-04-19. The other tables in the original Kaggle export (themes, ratings distributions, user ratings, creators) are not used in this project and were excluded to keep the repo size manageable. To re-fetch the full dataset:
  ```bash
  kaggle datasets download -d threnjen/board-games-database-from-boardgamegeek -p data/bgg/ --unzip
  ```
