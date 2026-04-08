# Claude Code Instructions

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

### Dataclass field definitions
Align field names, type annotations, and default values in columns:
```python
@dataclass(frozen = True)
class BonusEffect:
    resource_discount:      dict[Resource, int]       = field(default_factory = dict)
    resource_discount_any:  int                       = 0
    skip_next_complication: bool                      = False
    negates_volcano_card:   Optional[VolcanoCardName] = None
```

### Multi-line constructor calls
Align `=` signs within a single multi-line call:
```python
Mission(
    name               = MissionName.FETCH_WATER,
    required_resources = {Resource.ROPE: 2, Resource.WOOD: 1},
    players_count      = 3,
    required_tools     = [Tool.VESSEL],
)
```

### Variable assignments
No column alignment for variable assignments anywhere (function bodies, module level, notebook cells, loop bodies) — just one space around `=`. This applies even when variables have inline comments:
```python
# Correct
mission_name = select_mission(state)
mission = MISSIONS[mission_name]

BASE_MINUTES_PER_ROUND = 2.0   # fixed overhead
MINUTES_PER_PLAYER = 0.5   # per player

resource_labels = [r.name.title() for r in RESOURCES]
consumed_means = [data[f"consumed_{r.name}"].mean() for r in RESOURCES]
consumed_stds = [data[f"consumed_{r.name}"].std() for r in RESOURCES]

# Wrong — padding to align = signs or inline comments across rows
mission_name = select_mission(state)
mission      = MISSIONS[mission_name]

BASE_MINUTES_PER_ROUND = 2.0   # fixed overhead
MINUTES_PER_PLAYER     = 0.5   # per player

resource_labels = [r.name.title() for r in RESOURCES]
consumed_means  = [data[f"consumed_{r.name}"].mean() for r in RESOURCES]
consumed_stds   = [data[f"consumed_{r.name}"].std() for r in RESOURCES]
```

Column alignment is only allowed in **dataclass field definitions** and **multi-line constructor calls** (see above).

### Single-line constructor calls
No padding between arguments — just one space after each comma. Never add spaces to align arguments across different calls:
```python
# Correct
VolcanoCard(name = VolcanoCardName.TREMOR, discard_mission = True)
VolcanoCard(name = VolcanoCardName.ASH_IN_THE_AIR, extra_exhaustion_rounds = 1)

# Wrong — padding to align the second argument across rows
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
No padding on dict keys — just one space after the colon:
```python
MISSIONS: dict[MissionName, Mission] = {
    MissionName.LIGHT_A_FIRE: Mission(...),
    MissionName.TORCH_FOR_THE_NIGHT: Mission(...),
    MissionName.HUNT: Mission(...),
}
```

### Mutable defaults in dataclasses
Always use `field(default_factory = ...)` for mutable defaults — never bare `[]` or `{}`:
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

for res in resources:     # loop iterator — short name fine
    ...

# Wrong — abbreviations
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
scores high on average — they score well but inconsistently
```
