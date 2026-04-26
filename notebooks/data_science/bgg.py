"""Helpers for working with the BoardGameGeek dataset.

Used from the per-hypothesis notebooks under `notebooks/data_science/hypotheses/`.
"""


def reformat_columns(columns):
    """Strip BGG's column-name idiosyncrasies so columns become valid Python identifiers.

    Handles three patterns:
    - Colons followed by a lowercase letter (e.g. `Rank:strategygames`) are collapsed
      by uppercasing the next character and removing the colon.
    - Other colons (e.g. `Cat:Strategy`) are simply removed.
    - Spaces and hyphens (e.g. `Semi-Cooperative Game`) are removed.
    """
    return (columns
            .str.replace(r":([a-z])", lambda m: m.group(1).upper(), regex = True)
            .str.replace(":", "")
            .str.replace(" ", "")
            .str.replace("-", ""))
