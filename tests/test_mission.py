import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.missions import Mission
from simulation_engine.models.complications import ComplicationCard
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.models.records import MissionRequirement
from simulation_engine.mechanics.requirements import (
    compute_per_player_requirements, compute_complication_extras, compute_volcano_extras,
)
from simulation_engine.mechanics.affordability import apply_character_discounts, can_afford
from simulation_engine.mechanics.deductions import deduct_costs


# ── Constants ────────────────────────────────────────────────────────────────

CALM_BREEZE = ComplicationCard.get(ComplicationCardName.CALM_BREEZE)
MOSQUITO_ATTACK = ComplicationCard.get(ComplicationCardName.MOSQUITO_ATTACK)
WET_WOOD = ComplicationCard.get(ComplicationCardName.WET_WOOD)
SLIPPERY_ROCKS = ComplicationCard.get(ComplicationCardName.SLIPPERY_ROCKS)
HEAT_AND_THIRST = ComplicationCard.get(ComplicationCardName.HEAT_AND_THIRST)

LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
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


# ── compute_per_player_requirements ──────────────────────────────────────────

class TestComputePerPlayerRequirements:

    def test_base_requirements_no_modifiers(self):
        state = make_state([])

        result = compute_per_player_requirements(LIGHT_A_FIRE, state)

        assert result.typed == { Resource.WOOD: 1 }
        assert result.any_extra == 0

    def test_character_discounts_not_applied(self):
        state = make_state([])

        result = compute_per_player_requirements(LIGHT_A_FIRE, state)

        assert result.typed == { Resource.WOOD: 1 }


# ── compute_complication_extras (per-participant) ────────────────────────────

class TestComputeComplicationExtras:

    def test_no_complication_returns_zero_extras(self):
        result = compute_complication_extras(LIGHT_A_FIRE, None)

        assert result.typed == {}
        assert result.any_extra == 0

    def test_calm_breeze_no_extras(self):
        result = compute_complication_extras(LIGHT_A_FIRE, CALM_BREEZE)

        assert result.typed == {}
        assert result.any_extra == 0

    def test_mosquito_attack_typed_extra_per_participant(self):
        result = compute_complication_extras(HUNT, MOSQUITO_ATTACK)

        assert result.typed == { Resource.ROPE: 1 }
        assert result.any_extra == 0

    def test_conditional_wet_wood_applies_when_mission_requires_wood(self):
        result = compute_complication_extras(LIGHT_A_FIRE, WET_WOOD)

        assert result.typed == { Resource.WOOD: 1 }

    def test_conditional_wet_wood_skipped_when_mission_does_not_require_wood(self):
        result = compute_complication_extras(HUNT, WET_WOOD)

        assert result.typed == {}

    def test_slippery_rocks_any_extra_per_participant(self):
        result = compute_complication_extras(LIGHT_A_FIRE, SLIPPERY_ROCKS)

        assert result.typed == {}
        assert result.any_extra == 2

    def test_heat_and_thirst_folds_per_participant_into_any_extra(self):
        result = compute_complication_extras(LIGHT_A_FIRE, HEAT_AND_THIRST)

        assert result.typed == {}
        assert result.any_extra == 1


# ── compute_volcano_extras (per-participant) ─────────────────────────────────

class TestComputeVolcanoExtras:

    def test_no_volcano_card_returns_empty(self):
        state = make_state([])

        result = compute_volcano_extras(LIGHT_A_FIRE, state)

        assert result.typed == {}
        assert result.any_extra == 0

    def test_rain_and_mud_applies_to_wood_mission(self):
        state = make_state([], pending_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        result = compute_volcano_extras(LIGHT_A_FIRE, state)

        assert result.typed[Resource.WOOD] == 2

    def test_rain_and_mud_conditional_skipped_when_mission_lacks_wood(self):
        state = make_state([], pending_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        result = compute_volcano_extras(HUNT, state)

        assert result.typed == {}

    def test_lava_flow_applies_unconditionally(self):
        state = make_state([], pending_volcano_card = VolcanoCardName.LAVA_FLOW)

        result = compute_volcano_extras(HUNT, state)

        assert result.typed[Resource.ROPE] == 1


# ── apply_character_discounts ────────────────────────────────────────────────

class TestApplyCharacterDiscounts:

    def test_builder_discount_reduces_wood_cost_and_bumps_counter(self):
        builder = make_player(Character.BUILDER, [Resource.STONE])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 0)

        result = apply_character_discounts([builder], requirements, BUILD_A_SHELTER)

        assert len(result) == 1
        _, personal = result[0]
        assert personal.typed.get(Resource.WOOD, 0) == 0
        assert builder.contribution.requirement_discounts_used == 1

    def test_builder_discount_only_bumps_its_own_player(self):
        builder = make_player(Character.BUILDER, [])
        cook = make_player(Character.COOK, [])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 0)

        apply_character_discounts([builder, cook], requirements, BUILD_A_SHELTER)

        assert builder.contribution.requirement_discounts_used == 1
        assert cook.contribution.requirement_discounts_used == 0

    def test_builder_discount_skipped_on_fire_mission(self):
        builder = make_player(Character.BUILDER, [Resource.WOOD])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 0)

        result = apply_character_discounts([builder], requirements, LIGHT_A_FIRE)

        _, personal = result[0]
        assert personal.typed.get(Resource.WOOD, 0) == 1
        assert builder.contribution.requirement_discounts_used == 0

    def test_fire_starter_discount_on_fire_mission(self):
        fire_starter = make_player(Character.FIRE_STARTER, [])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 2)

        result = apply_character_discounts([fire_starter], requirements, LIGHT_A_FIRE)

        _, personal = result[0]
        assert personal.any_extra == 1
        assert fire_starter.contribution.requirement_discounts_used == 1

    def test_fire_starter_no_discount_on_non_fire_mission(self):
        fire_starter = make_player(Character.FIRE_STARTER, [])
        requirements = MissionRequirement(typed = { Resource.STONE: 1, Resource.ROPE: 1 }, any_extra = 0)

        apply_character_discounts([fire_starter], requirements, HUNT)

        assert fire_starter.contribution.requirement_discounts_used == 0


# ── can_afford ───────────────────────────────────────────────────────────────

class TestCanAfford:

    def test_returns_true_when_all_checks_pass(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1, Resource.STONE: 1 }, any_extra = 0)
        player_requirements = apply_character_discounts([player_one, player_two], requirements, LIGHT_A_FIRE)

        assert can_afford(player_requirements, None, state) is True

    def test_returns_false_and_tracks_missing_typed(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.ROPE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1, Resource.STONE: 1 }, any_extra = 0)
        player_requirements = apply_character_discounts([player_one, player_two], requirements, LIGHT_A_FIRE)

        assert can_afford(player_requirements, None, state) is False
        assert state.mission_failures_by_resource.get(Resource.WOOD, 0) == 1

    def test_returns_false_and_tracks_insufficient_any_extra(self):
        player = make_player(Character.COOK, [Resource.WOOD])
        state = make_state([player])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 5)
        player_requirements = apply_character_discounts([player], requirements, LIGHT_A_FIRE)

        assert can_afford(player_requirements, None, state) is False
        assert state.mission_failures_any_extra == 1

    def test_max_per_type_cap_rejects_overloaded_hand(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD, Resource.WOOD])
        state = make_state([player])
        requirements = MissionRequirement(typed = { Resource.WOOD: 2 }, any_extra = 0)
        player_requirements = apply_character_discounts([player], requirements, LIGHT_A_FIRE)

        assert can_afford(player_requirements, 1, state) is False

    def test_can_afford_does_not_mutate_player_resources(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player])
        original_resources = list(player.resources)
        requirements = MissionRequirement(typed = { Resource.ROPE: 5 }, any_extra = 0)
        player_requirements = apply_character_discounts([player], requirements, LIGHT_A_FIRE)

        can_afford(player_requirements, None, state)

        assert player.resources == original_resources


# ── deduct_costs ─────────────────────────────────────────────────────────────

class TestDeductCosts:

    def test_deducts_typed_resources_per_player(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state([player_one, player_two])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1, Resource.STONE: 1 }, any_extra = 0)
        player_requirements = apply_character_discounts([player_one, player_two], requirements, LIGHT_A_FIRE)

        deduct_costs(player_requirements, state)

        assert player_one.resources == [Resource.ROPE]
        assert player_two.resources == []

    def test_deducts_any_extra_from_player_surplus(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE, Resource.ROPE])
        state = make_state([player])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 1)
        player_requirements = apply_character_discounts([player], requirements, LIGHT_A_FIRE)

        deduct_costs(player_requirements, state)

        assert len(player.resources) == 2

    def test_builder_discount_spares_wood_from_hand(self):
        builder = make_player(Character.BUILDER, [Resource.STONE])
        state = make_state([builder])
        requirements = MissionRequirement(typed = { Resource.WOOD: 1 }, any_extra = 0)
        player_requirements = apply_character_discounts([builder], requirements, BUILD_A_SHELTER)

        deduct_costs(player_requirements, state)

        assert builder.resources == [Resource.STONE]


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
