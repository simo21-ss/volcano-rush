import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.bonus_effects import BonusEffect
from simulation_engine.models.missions import Mission
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.agents.feasibility import AffordLevel, player_afford_level, team_can_afford


# ── Constants ────────────────────────────────────────────────────────────────

LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
FETCH_WATER = Mission.get(MissionName.FETCH_WATER)
GATHER_MATERIALS = Mission.get(MissionName.GATHER_MATERIALS)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_player(character: Character, resources: list[Resource]) -> Player:
    return Player(character = character, resources = list(resources))


def make_state(players: list[Player], **overrides) -> GameState:
    defaults = {
        "players": players,
        "active_missions": [],
        "resource_deck": [],
        "complication_deck": list(ComplicationCardName),
        "volcano_deck": list(VolcanoCardName),
        "tools": { Tool.KNIFE: ToolState(), Tool.VESSEL: ToolState() },
        "boat_parts_required": 4,
    }
    defaults.update(overrides)
    return GameState(**defaults)


# ── player_afford_level ──────────────────────────────────────────────────────

class TestPlayerAffordLevel:

    def test_exact_match(self):
        player = make_player(Character.COOK, [Resource.WOOD])
        state = make_state([player])

        assert player_afford_level(player, LIGHT_A_FIRE, state) == AffordLevel.EXACT

    def test_surplus_hand(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE])
        state = make_state([player])

        assert player_afford_level(player, LIGHT_A_FIRE, state) == AffordLevel.SURPLUS

    def test_cannot_afford_missing_typed_resource(self):
        player = make_player(Character.COOK, [Resource.STONE, Resource.ROPE])
        state = make_state([player])

        assert player_afford_level(player, LIGHT_A_FIRE, state) == AffordLevel.CANNOT_AFFORD

    def test_cannot_afford_empty_hand(self):
        player = make_player(Character.COOK, [])
        state = make_state([player])

        assert player_afford_level(player, LIGHT_A_FIRE, state) == AffordLevel.CANNOT_AFFORD

    def test_cannot_afford_empty_hand_zero_cost_mission(self):
        # A hypothetical zero-cost mission would classify an empty hand as
        # EXACT. None of the real missions have zero base cost, but verify the
        # boundary: cost of 1 typed on empty hand is CANNOT_AFFORD.
        player = make_player(Character.COOK, [])
        state = make_state([player])

        assert player_afford_level(player, HUNT, state) == AffordLevel.CANNOT_AFFORD

    def test_builder_discount_enables_affordability(self):
        # Builder with only a STONE cannot satisfy LIGHT_A_FIRE (wants 1 WOOD)
        # by their raw hand. The Builder's per-player discount drops the wood
        # cost to 0, so the STONE is classified as surplus.
        builder = make_player(Character.BUILDER, [Resource.STONE])
        state = make_state([builder])

        assert player_afford_level(builder, LIGHT_A_FIRE, state) == AffordLevel.SURPLUS

    def test_builder_discount_empty_hand_is_exact(self):
        # Builder with no resources on a WOOD-only mission: discount reduces
        # cost to 0, player pays nothing, hand fits exactly.
        builder = make_player(Character.BUILDER, [])
        state = make_state([builder])

        assert player_afford_level(builder, LIGHT_A_FIRE, state) == AffordLevel.EXACT

    def test_pending_bonus_reduces_requirement(self):
        player = make_player(Character.COOK, [Resource.STONE])
        state = make_state(
            [player],
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        assert player_afford_level(player, LIGHT_A_FIRE, state) == AffordLevel.SURPLUS

    def test_pending_bonus_not_consumed_by_feasibility_query(self):
        # Regression: the old code consumed state.pending_bonus inside
        # compute_per_player_requirements, which silently evaporated the bonus
        # during voting.
        player = make_player(Character.COOK, [Resource.STONE])
        state = make_state(
            [player],
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        player_afford_level(player, LIGHT_A_FIRE, state)
        player_afford_level(player, LIGHT_A_FIRE, state)

        assert state.pending_bonus is not None
        assert state.pending_bonus.resource_discount == { Resource.WOOD: 1 }

    def test_classification_stable_across_missions_with_shared_bonus(self):
        # Simulates vote_for_mission iterating over active missions. Whichever
        # order missions are evaluated in, feasibility classifications should
        # stay consistent because the bonus is a pure read, not a consume.
        player = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE])
        state = make_state(
            [player],
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        first = player_afford_level(player, LIGHT_A_FIRE, state)
        second = player_afford_level(player, HUNT, state)
        third = player_afford_level(player, LIGHT_A_FIRE, state)

        assert first == third
        # HUNT requires STONE and ROPE; player has WOOD and ROPE -> missing STONE.
        assert second == AffordLevel.CANNOT_AFFORD


# ── team_can_afford ──────────────────────────────────────────────────────────

class TestTeamCanAfford:

    def test_team_can_afford_when_enough_participants_have_resources(self):
        players = [
            make_player(Character.COOK, [Resource.WOOD]),
            make_player(Character.COOK, [Resource.WOOD]),
            make_player(Character.COOK, [Resource.STONE]),
        ]
        state = make_state(players)

        # LIGHT_A_FIRE needs 2 participants with WOOD; two cooks have WOOD.
        assert team_can_afford(LIGHT_A_FIRE, state) is True

    def test_team_cannot_afford_when_too_few_players_have_resources(self):
        players = [
            make_player(Character.COOK, [Resource.WOOD]),
            make_player(Character.COOK, [Resource.STONE]),
            make_player(Character.COOK, [Resource.STONE]),
        ]
        state = make_state(players)

        assert team_can_afford(LIGHT_A_FIRE, state) is False

    def test_team_cannot_afford_when_required_tool_damaged(self):
        players = [
            make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]),
            make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]),
            make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]),
        ]
        state = make_state(players)
        state.tools[Tool.VESSEL].damaged = True

        # FETCH_WATER requires the VESSEL tool.
        assert team_can_afford(FETCH_WATER, state) is False

    def test_exhausted_players_do_not_count_toward_staffing(self):
        affordable = make_player(Character.COOK, [Resource.WOOD])
        affordable_but_exhausted = make_player(Character.COOK, [Resource.WOOD])
        affordable_but_exhausted.is_exhausted = True
        unaffordable = make_player(Character.COOK, [Resource.STONE])
        state = make_state([affordable, affordable_but_exhausted, unaffordable])

        # Only one non-exhausted player can afford LIGHT_A_FIRE, which needs 2.
        assert team_can_afford(LIGHT_A_FIRE, state) is False

    def test_pending_bonus_enlarges_feasible_team(self):
        players = [
            make_player(Character.COOK, [Resource.STONE]),
            make_player(Character.COOK, [Resource.STONE]),
        ]
        # Without the bonus the team could not afford LIGHT_A_FIRE (needs WOOD).
        state_no_bonus = make_state(players)
        state_with_bonus = make_state(
            players,
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        assert team_can_afford(LIGHT_A_FIRE, state_no_bonus) is False
        assert team_can_afford(LIGHT_A_FIRE, state_with_bonus) is True
