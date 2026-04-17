import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionType, MissionName,
    ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.bonus_effects import BonusEffect
from simulation_engine.models.missions import Mission
from simulation_engine.models.complications import ComplicationCard
from simulation_engine.models.volcano import VolcanoCard
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.models.records import MissionRequirement
from simulation_engine.mechanics.mission import compute_per_player_requirements, compute_group_extras, check_and_contribute, resolve_mission


# ── Constants ────────────────────────────────────────────────────────────────

CALM_BREEZE = ComplicationCard.get(ComplicationCardName.CALM_BREEZE)
LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
FETCH_WATER = Mission.get(MissionName.FETCH_WATER)
NO_EXTRAS = MissionRequirement(typed = {}, any_extra = 0)


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

class TestComputePerPlayerRequirements:

    def test_base_requirements_no_modifiers(self):
        state = make_state([])

        result = compute_per_player_requirements(LIGHT_A_FIRE, state)

        assert result.typed == {Resource.WOOD: 1}
        assert result.any_extra == 0

    def test_bonus_discount_applied(self):
        state = make_state([], pending_bonus = BonusEffect(resource_discount = {Resource.WOOD: 1}))

        result = compute_per_player_requirements(LIGHT_A_FIRE, state)

        assert result.typed.get(Resource.WOOD, 0) == 0

    def test_character_discounts_not_applied(self):
        """Per-player requirements do not include character discounts - applied in check_and_contribute."""
        state = make_state([])

        result = compute_per_player_requirements(LIGHT_A_FIRE, state)

        assert result.typed == {Resource.WOOD: 1}


class TestComputeGroupExtras:

    def test_calm_breeze_no_extras(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players)

        result = compute_group_extras(LIGHT_A_FIRE, CALM_BREEZE, players, state)

        assert result.typed == {}
        assert result.any_extra == 0

    def test_complication_adds_typed_resource(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players)
        mosquito_attack = ComplicationCard.get(ComplicationCardName.MOSQUITO_ATTACK)

        result = compute_group_extras(LIGHT_A_FIRE, mosquito_attack, players, state)

        assert result.typed[Resource.ROPE] == 1

    def test_conditional_complication_applies_when_resource_present(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players)
        wet_wood = ComplicationCard.get(ComplicationCardName.WET_WOOD)

        result = compute_group_extras(LIGHT_A_FIRE, wet_wood, players, state)

        assert result.typed[Resource.WOOD] == 1

    def test_conditional_complication_skipped_when_resource_absent(self):
        players = [make_player(Character.COOK, [Resource.STONE])]
        state = make_state(players)
        wet_wood = ComplicationCard.get(ComplicationCardName.WET_WOOD)

        result = compute_group_extras(HUNT, wet_wood, players, state)

        assert result.typed == {}

    def test_volcano_card_adds_conditional_extra(self):
        players = [make_player(Character.COOK, [Resource.WOOD])]
        state = make_state(players, pending_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        result = compute_group_extras(LIGHT_A_FIRE, CALM_BREEZE, players, state)

        assert result.typed[Resource.WOOD] == 2


# ── check_and_contribute ─────────────────────────────────────────────────────

class TestCheckAndContribute:

    def test_success_deducts_typed_resources_per_player(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1, Resource.STONE: 1}, any_extra = 0)

        result = check_and_contribute([player_one, player_two], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is True
        assert player_one.resources == [Resource.ROPE]
        assert player_two.resources == []

    def test_failure_one_player_insufficient_typed_resource(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.ROPE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1, Resource.STONE: 1}, any_extra = 0)

        result = check_and_contribute([player_one, player_two], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is False
        assert state.mission_failures_by_resource.get(Resource.WOOD, 0) == 1

    def test_any_extra_filled_from_player_surplus(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE, Resource.ROPE])
        state = make_state([player])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 1)

        result = check_and_contribute([player], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is True
        assert len(player.resources) == 2

    def test_failure_insufficient_any_extra(self):
        player = make_player(Character.COOK, [Resource.WOOD])
        state = make_state([player])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 5)

        result = check_and_contribute([player], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is False
        assert state.mission_failures_any_extra == 1

    def test_max_per_type_caps_per_player(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD, Resource.WOOD])
        state = make_state([player])
        requirements = MissionRequirement(typed = {Resource.WOOD: 2}, any_extra = 0)

        result = check_and_contribute([player], requirements, NO_EXTRAS, 1, state, LIGHT_A_FIRE)

        assert result is False

    def test_no_mutation_on_failure(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player])
        original_resources = list(player.resources)
        requirements = MissionRequirement(typed = {Resource.ROPE: 5}, any_extra = 0)

        result = check_and_contribute([player], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is False
        assert player.resources == original_resources

    def test_builder_discount_applied_per_player(self):
        builder = make_player(Character.BUILDER, [Resource.STONE])
        state = make_state([builder])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 0)

        result = check_and_contribute([builder], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is True
        assert builder.resources == [Resource.STONE]
        assert builder.contribution.requirement_discounts_used == 1

    def test_builder_discount_does_not_affect_other_players(self):
        builder = make_player(Character.BUILDER, [Resource.STONE])
        cook = make_player(Character.COOK, [Resource.ROPE])
        state = make_state([builder, cook])
        requirements = MissionRequirement(typed = {Resource.WOOD: 1}, any_extra = 0)

        result = check_and_contribute([builder, cook], requirements, NO_EXTRAS, None, state, LIGHT_A_FIRE)

        assert result is False

    def test_fire_starter_discount_on_fire_mission(self):
        fire_starter = make_player(Character.FIRE_STARTER, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state([fire_starter])
        slippery_rocks = ComplicationCard.get(ComplicationCardName.SLIPPERY_ROCKS)
        per_player = compute_per_player_requirements(LIGHT_A_FIRE, state)
        group_extras = compute_group_extras(LIGHT_A_FIRE, slippery_rocks, [fire_starter], state)

        result = check_and_contribute([fire_starter], per_player, group_extras, None, state, LIGHT_A_FIRE)

        assert result is True
        assert fire_starter.contribution.requirement_discounts_used == 1

    def test_fire_starter_no_discount_on_non_fire_mission(self):
        fire_starter = make_player(Character.FIRE_STARTER, [Resource.STONE, Resource.ROPE])
        state = make_state([fire_starter])
        requirements = MissionRequirement(typed = {Resource.STONE: 1, Resource.ROPE: 1}, any_extra = 0)

        result = check_and_contribute([fire_starter], requirements, NO_EXTRAS, None, state, HUNT)

        assert result is True
        assert fire_starter.contribution.requirement_discounts_used == 0


# ── resolve_mission ──────────────────────────────────────────────────────────

class TestResolveMission:

    def test_resolve_success_simple(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state([player_one, player_two])

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert result is True

    def test_resolve_fails_wrong_participant_count(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_three = make_player(Character.SAILOR, [Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two, player_three])

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two, player_three], CALM_BREEZE)

        assert result is False

    def test_resolve_fails_damaged_tool(self):
        player_one = make_player(Character.COOK, [Resource.ROPE, Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.ROPE, Resource.WOOD, Resource.STONE])
        player_three = make_player(Character.SAILOR, [Resource.ROPE, Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two, player_three])
        state.tools[Tool.VESSEL].damaged = True

        result = resolve_mission(state, FETCH_WATER, [player_one, player_two, player_three], CALM_BREEZE)

        assert result is False
        assert state.mission_failures_tool_damaged.get(Tool.VESSEL, 0) == 1

    def test_resolve_complication_damages_tool_on_success(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state([player_one, player_two])
        blunt_blade = ComplicationCard.get(ComplicationCardName.BLUNT_BLADE)

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], blunt_blade)

        assert result is True
        assert state.tools[Tool.KNIFE].damaged is True

    def test_resolve_fails_when_one_player_cannot_afford(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.ROPE])
        state = make_state([player_one, player_two])

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert result is False


# ── Cook bonus points ───────────────────────────────────────────────────────

from simulation_engine.characters import CookStrategy

RAISE_THE_MAST = Mission.get(MissionName.RAISE_THE_MAST)


class TestCookBonusPoints:

    def test_cook_bonus_on_food_mission(self):
        cook_strategy = CookStrategy()

        assert cook_strategy.mission_success_bonus_points(HUNT) == 1

    def test_cook_no_bonus_on_vessel_boat_mission(self):
        cook_strategy = CookStrategy()

        assert cook_strategy.mission_success_bonus_points(RAISE_THE_MAST) == 0

    def test_cook_no_bonus_on_fire_mission(self):
        cook_strategy = CookStrategy()

        assert cook_strategy.mission_success_bonus_points(LIGHT_A_FIRE) == 0

    def test_cook_prefers_food_mission(self):
        cook_strategy = CookStrategy()

        preferred = cook_strategy.preferred_mission([MissionName.LIGHT_A_FIRE, MissionName.HUNT])

        assert preferred == MissionName.HUNT

    def test_cook_no_preference_without_food_mission(self):
        cook_strategy = CookStrategy()

        preferred = cook_strategy.preferred_mission([MissionName.LIGHT_A_FIRE, MissionName.RAISE_THE_MAST])

        assert preferred is None
