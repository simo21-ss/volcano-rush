import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.missions import Mission
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.agents.feasibility import AffordLevel, player_afford_level, team_can_afford


# ── Constants ────────────────────────────────────────────────────────────────

LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
FETCH_WATER = Mission.get(MissionName.FETCH_WATER)
GATHER_MATERIALS = Mission.get(MissionName.GATHER_MATERIALS)
CUT_THE_KEEL = Mission.get(MissionName.CUT_THE_KEEL)
BUILD_A_SHELTER = Mission.get(MissionName.BUILD_A_SHELTER)


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

    def test_builder_discount_enables_affordability_on_shelter_mission(self):
        # Builder with [ROPE, STONE] on BUILD_A_SHELTER (WOOD + STONE) gets the
        # WOOD requirement dropped to 0. STONE pays the typed stone cost; ROPE
        # is left over, classifying the hand as SURPLUS.
        builder = make_player(Character.BUILDER, [Resource.ROPE, Resource.STONE])
        state = make_state([builder])

        assert player_afford_level(builder, BUILD_A_SHELTER, state) == AffordLevel.SURPLUS

    def test_builder_discount_minimal_hand_is_exact_on_boat_mission(self):
        # Builder with [ROPE] on CUT_THE_KEEL (WOOD + ROPE) gets WOOD dropped to
        # 0. The single ROPE covers the remaining typed cost exactly.
        builder = make_player(Character.BUILDER, [Resource.ROPE])
        state = make_state([builder])

        assert player_afford_level(builder, CUT_THE_KEEL, state) == AffordLevel.EXACT

    def test_builder_discount_does_not_apply_to_fire_mission(self):
        # Builder's wood discount is scoped to SHELTER and BOAT missions. On
        # LIGHT_A_FIRE (FIRE type), the discount does not trigger, so a player
        # with only STONE cannot satisfy the 1 WOOD typed requirement.
        builder = make_player(Character.BUILDER, [Resource.STONE])
        state = make_state([builder])

        assert player_afford_level(builder, LIGHT_A_FIRE, state) == AffordLevel.CANNOT_AFFORD

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

