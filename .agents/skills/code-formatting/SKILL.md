---
name: code-formatting
description: Project formatting rules for Python (keyword arg spacing, no column alignment anywhere, dict/list literal style, no abbreviated variable names, dataclass field ordering), Git (no Co-Authored-By), and Markdown (plain hyphens instead of em/en dashes). Invoke before editing any .py or .md file in this repo.
---

# Code Formatting Rules

## Python Formatting

### Keyword arguments
Always use spaces around `=` in keyword arguments and decorator arguments:
```python
# Correct
@dataclass(frozen = True)
field(default_factory = dict)
BonusEffect(boat_part = True)
Mission(name = MissionName.HUNT, players_count = 3)

# Wrong
@dataclass(frozen=True)
field(default_factory=dict)
```

### No column alignment anywhere
Never pad with spaces to align `=` signs, type annotations, field names, default values, or inline comments across rows. This applies to every context: dataclass field definitions, multi-line constructor calls, function signatures, variable assignments, module-level constants, notebook cells, loop bodies.

One space before and after each `=`. One space after each comma. That is the only horizontal spacing rule.

```python
# Correct - dataclass fields, no alignment padding
@dataclass(frozen = True)
class BonusEffect:
    resource_discount: dict[Resource, int] = field(default_factory = dict)
    resource_discount_any: int = 0
    skip_next_complication: bool = False
    negates_volcano_card: Optional[VolcanoCardName] = None

# Correct - multi-line constructor, no alignment padding
Mission(
    name = MissionName.FETCH_WATER,
    required_resources = {Resource.ROPE: 2, Resource.WOOD: 1},
    players_count = 3,
    required_tools = [Tool.VESSEL],
)

# Correct - function signature, no alignment padding, 8-space continuation indent
def run_game(
        player_count: int,
        initial_resources_per_player: int = 3,
        deck_resource_count: int = 20,
        urgent_volcano_threshold: int = 4,
        verbose: bool = False,
) -> GameRecord:
    ...

# Correct - variable assignments with inline comments
BASE_MINUTES_PER_ROUND = 2.0   # fixed overhead
MINUTES_PER_PLAYER = 0.5   # per player

# Wrong - padding to align = signs across rows
resource_discount:      dict[Resource, int]       = field(default_factory = dict)
resource_discount_any:  int                       = 0
skip_next_complication: bool                      = False

# Wrong - padding to align = signs in a constructor call
Mission(
    name               = MissionName.FETCH_WATER,
    required_resources = {Resource.ROPE: 2, Resource.WOOD: 1},
    players_count      = 3,
)

# Wrong - padding to align comments
BASE_MINUTES_PER_ROUND = 2.0   # fixed overhead
MINUTES_PER_PLAYER     = 0.5   # per player
```

### Multi-line function signatures
Parameters on continuation lines are indented with **8 spaces** (two indent levels), matching PyCharm's default continuation-indent setting. The closing `)` sits at column 0. Applies to both `def` declarations and multi-line signatures on method definitions inside classes (8 spaces beyond the class body's indent level):
```python
# Correct - top-level function, 8-space continuation indent
def run_scenario(
        player_count: int,
        n_games: int,
        base_seed: Optional[int] = None,
) -> list[GameRecord]:
    ...

# Wrong - 4-space continuation indent
def run_scenario(
    player_count: int,
    n_games: int,
) -> list[GameRecord]:
    ...
```

### Single-line constructor calls
No padding between arguments - just one space after each comma. Never add spaces to align arguments across different calls:
```python
# Correct
VolcanoCard(name = VolcanoCardName.TREMOR, discard_mission = True)
VolcanoCard(name = VolcanoCardName.ASH_IN_THE_AIR, extra_exhaustion_rounds = 1)

# Wrong - padding to align the second argument across rows
VolcanoCard(name = VolcanoCardName.TREMOR,         discard_mission = True)
VolcanoCard(name = VolcanoCardName.ASH_IN_THE_AIR, extra_exhaustion_rounds = 1)
```

### Dict and list literals
Prefer `{}` over `dict(...)` and `[]` over `list(...)` for literal construction:
```python
# Correct
{"facecolor": "#a8d5a2", "color": "black"}
[]

# Wrong
dict(facecolor = "#a8d5a2", color = "black")
list()
```

### Dict keys
No padding on dict keys - just one space after the colon:
```python
MISSIONS: dict[MissionName, Mission] = {
    MissionName.LIGHT_A_FIRE: Mission(...),
    MissionName.TORCH_FOR_THE_NIGHT: Mission(...),
    MissionName.HUNT: Mission(...),
}
```

### Mutable defaults in dataclasses
Always use `field(default_factory = ...)` for mutable defaults - never bare `[]` or `{}`:
```python
# Correct
resources:       list[Resource]     = field(default_factory = list)
extra_resources: dict[Resource, int] = field(default_factory = dict)

# Wrong
resources:       list[Resource]     = []
extra_resources: dict[Resource, int] = {}
```

### Variable naming
Never use abbreviations in variable names. Write full, descriptive names so code reads naturally without needing to decode shorthand. The only exception is loop iterators in `for` statements:
```python
# Correct
resource_requirements = dict(mission.required_resources)
points = base_pts + (1 if fire_bonus else 0)
is_ash_in_the_air = state.pending_volcano_card == VolcanoCardName.ASH_IN_THE_AIR

for res in resources:     # loop iterator - short name fine
    ...

# Wrong - abbreviations
req = dict(mission.required_resources)
pts = base_pts + (1 if fire_bonus else 0)
ash = state.pending_volcano_card == VolcanoCardName.ASH_IN_THE_AIR
```

### Field ordering in dataclasses
Fields without defaults must come before fields with defaults:
```python
# Correct
@dataclass(frozen = True)
class Mission:
    name:               MissionName          # no default
    required_resources: dict[Resource, int]  # no default
    players_count:      int                  # no default
    required_tools:     list[Tool]           = field(default_factory = list)  # has default
    is_boat_mission:    bool                 = False                           # has default
```

## Git

### Commit messages
Never add "Co-Authored-By" or any similar attribution lines to commit messages.

## Markdown Text

### Special characters
Use plain hyphens (`-`) instead of em-dashes or en-dashes in all markdown text:
```markdown
# Correct
scores high on average - they score well but inconsistently

# Wrong
scores high on average - they score well but inconsistently
```