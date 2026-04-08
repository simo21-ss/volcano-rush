import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionType, MissionName,
    ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.cards import Mission, ComplicationCard, VolcanoCard, BonusEffect
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.models.records import MissionRequirement
from simulation_engine.mechanics.mission import compute_requirements, check_and_contribute, resolve_mission


# ── Constants ────────────────────────────────────────────────────────────────

CALM_BREEZE = ComplicationCard.get(ComplicationCardName.CALM_BREEZE)
LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
FETCH_WATER = Mission.get(MissionName.FETCH_WATER)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_player(character: Character, resources: list[Resource]) -> Player:
    return Player(character = character, resources = list(resources))


def make_state(players: list[Player], **overrides) -> GameState:
    defaults = {
        "players":            players,
        "active_missions":    [],
        "resource_deck":      [],
        "complication_deck":  list(ComplicationCardName),
        "volcano_deck":       list(VolcanoCardName),
        "tools":              {Tool.KNIFE: ToolState(), Tool.VESSEL: ToolState()},
        "boat_parts_required": 4,
    }
    defaults.update(overrides)
    return GameState(**defaults)


# ── compute_requirements ─────────────────────────────────────────────────────

class TestComputeRequirements:

    def test_base_requirements_no_modifiers(self):
        players = [make_player(Character.COOK, [Resource.WOOD, Resource.STONE])]
        state = make_state(players)

        result = compute_requirements(LIGHT_A_FIRE, players, CALM_BREEZE, state)

        assert result.typed == {Resource.WOOD: 2, Resource.STONE: 1}
        assert result.any_extra == 0

    def test_complication_adds_typed_resource(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players)
        mosquito_attack = ComplicationCard.get(ComplicationCardName.MOSQUITO_ATTACK)

        result = compute_requirements(LIGHT_A_FIRE, players, mosquito_attack, state)

        assert result.typed[Resource.ROPE] == 1
        assert result.typed[Resource.WOOD] == 2
        assert result.typed[Resource.STONE] == 1

    def test_conditional_complication_applies_when_resource_present(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players)
        wet_wood = ComplicationCard.get(ComplicationCardName.WET_WOOD)

        result = compute_requirements(LIGHT_A_FIRE, players, wet_wood, state)

        assert result.typed[Resource.WOOD] == 3

    def test_conditional_complication_skipped_when_resource_absent(self):
        players = [make_player(Character.COOK, [Resource.STONE])]
        state = make_state(players)
        wet_wood = ComplicationCard.get(ComplicationCardName.WET_WOOD)

        result = compute_requirements(HUNT, players, wet_wood, state)

        assert result.typed == {Resource.STONE: 2, Resource.ROPE: 2}

    def test_volcano_card_adds_conditional_extra(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players, pending_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        result = compute_requirements(LIGHT_A_FIRE, players, CALM_BREEZE, state)

        assert result.typed[Resource.WOOD] == 4

    def test_builder_discount_applied_when_wood_gte_2(self):
        players = [make_player(Character.BUILDER, [Resource.WOOD])]
        state = make_state(players)

        result = compute_requirements(LIGHT_A_FIRE, players, CALM_BREEZE, state)

        assert result.typed[Resource.WOOD] == 1

    def test_fire_starter_discount_on_fire_mission(self):
        players = [make_player(Character.FIRE_STARTER, [Resource.WOOD])]
        state = make_state(players)
        slippery_rocks = ComplicationCard.get(ComplicationCardName.SLIPPERY_ROCKS)

        result = compute_requirements(LIGHT_A_FIRE, players, slippery_rocks, state)

        assert result.any_extra == 1


# ── check_and_contribute ─────────────────────────────────────────────────────

class TestCheckAndContribute:

    def test_success_deducts_typed_resources(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.BUILDER, [Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = {Resource.WOOD: 2, Resource.STONE: 1}, any_extra = 0)

        result = check_and_contribute([player_one, player_two], requirements, None, state)

        assert result is True
        all_remaining = player_one.resources + player_two.resources
        assert all_remaining.count(Resource.WOOD) == 0
        assert all_remaining.count(Resource.STONE) <= 1

    def test_failure_insufficient_typed_resource(self):
        player_one = make_player(Character.COOK, [Resource.STONE])
        player_two = make_player(Character.BUILDER, [Resource.STONE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = {Resource.STONE: 3}, any_extra = 0)

        result = check_and_contribute([player_one, player_two], requirements, None, state)

        assert result is False
        assert state.mission_failures_by_resource.get(Resource.STONE, 0) == 1

    def test_any_extra_filled_from_surplus(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state([player])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 2)

        result = check_and_contribute([player], requirements, None, state)

        assert result is True
        assert len(player.resources) == 1

    def test_failure_insufficient_any_extra(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 5)

        result = check_and_contribute([player], requirements, None, state)

        assert result is False
        assert state.mission_failures_any_extra == 1

    def test_max_per_type_caps_contribution(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD, Resource.WOOD])
        player_two = make_player(Character.BUILDER, [Resource.WOOD, Resource.WOOD, Resource.WOOD])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = {Resource.WOOD: 3}, any_extra = 0)

        result = check_and_contribute([player_one, player_two], requirements, 1, state)

        assert result is False

    def test_participation_cost_forces_minimum_payment(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.BUILDER, [Resource.ROPE, Resource.STONE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 0)

        original_total = len(player_one.resources) + len(player_two.resources)
        result = check_and_contribute([player_one, player_two], requirements, None, state)

        assert result is True
        remaining_total = len(player_one.resources) + len(player_two.resources)
        assert remaining_total <= original_total - 2

    def test_no_mutation_on_failure(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player])
        original_resources = list(player.resources)
        requirements = MissionRequirement(typed = {Resource.ROPE: 5}, any_extra = 0)

        result = check_and_contribute([player], requirements, None, state)

        assert result is False
        assert player.resources == original_resources


# ── resolve_mission ──────────────────────────────────────────────────────────

class TestResolveMission:

    def test_resolve_success_simple(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.BUILDER, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state([player_one, player_two])

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert result is True

    def test_resolve_fails_wrong_participant_count(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.BUILDER, [Resource.WOOD, Resource.STONE])
        player_three = make_player(Character.SAILOR, [Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two, player_three])

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two, player_three], CALM_BREEZE)

        assert result is False

    def test_resolve_fails_damaged_tool(self):
        player_one = make_player(Character.COOK, [Resource.ROPE, Resource.ROPE, Resource.WOOD])
        player_two = make_player(Character.BUILDER, [Resource.ROPE, Resource.WOOD, Resource.STONE])
        player_three = make_player(Character.SAILOR, [Resource.ROPE, Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two, player_three])
        state.tools[Tool.VESSEL].damaged = True

        result = resolve_mission(state, FETCH_WATER, [player_one, player_two, player_three], CALM_BREEZE)

        assert result is False
        assert state.mission_failures_tool_damaged.get(Tool.VESSEL, 0) == 1

    def test_resolve_complication_damages_tool_on_success(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.BUILDER, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state([player_one, player_two])
        blunt_blade = ComplicationCard.get(ComplicationCardName.BLUNT_BLADE)

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], blunt_blade)

        assert result is True
        assert state.tools[Tool.KNIFE].damaged is True
