# Volcano Rush - Simulation Modeling Assumptions

The following clarifications and assumptions are used in the Monte Carlo simulation where the original rules are ambiguous.

| Rule Area | Assumption |
|---|---|
| **Exhaustion** | Applies to all mission participants after resolution, regardless of success or failure |
| **Craftsman repair timeline** | Round N: repair starts. Round N+1: tool still unavailable. Round N+2: tool available again |
| **Sailor - lesser evil** | The "lesser" Complication card is selected via a severity scoring function |
| **Participant count** | Treated as an exact requirement - missions need exactly the stated number of participants |
| **Unavailable tool** | If a mission requires a tool that is damaged, the mission automatically fails |
| **Night Anxiety (Complication)** | Requires 1 available non-participant helper; if none available, mission fails. Helper may contribute resources but receives no points |
| **Gather - default** | Gathering is the automatic action for any player who does not participate in the mission |
| **Gather - non-Gatherer** | Drawing 1 resource card via Gather does not cause Exhaustion |
| **Gather - Gatherer role** | Using the Gatherer's boosted draw (2 resources) causes Exhaustion |

> These assumptions can be adjusted via constants in the simulation code.
