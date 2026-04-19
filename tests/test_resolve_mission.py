import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName, ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.bonus_effects import BonusEffect
from simulation_engine.models.missions import Mission
from simulation_engine.models.complications import ComplicationCard
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.mechanics.mission import resolve_mission


# ── Constants ────────────────────────────────────────────────────────────────

CALM_BREEZE = ComplicationCard.get(ComplicationCardName.CALM_BREEZE)
MOSQUITO_ATTACK = ComplicationCard.get(ComplicationCardName.MOSQUITO_ATTACK)
WET_WOOD = ComplicationCard.get(ComplicationCardName.WET_WOOD)
SLIPPERY_ROCKS = ComplicationCard.get(ComplicationCardName.SLIPPERY_ROCKS)
HEAT_AND_THIRST = ComplicationCard.get(ComplicationCardName.HEAT_AND_THIRST)
BLUNT_BLADE = ComplicationCard.get(ComplicationCardName.BLUNT_BLADE)

LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
FETCH_WATER = Mission.get(MissionName.FETCH_WATER)


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


# ── resolve_mission happy path and short-circuit failures ────────────────────

class TestResolveMissionOutcomes:

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

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], BLUNT_BLADE)

        assert result is True
        assert state.tools[Tool.KNIFE].damaged is True

    def test_resolve_fails_when_one_player_cannot_afford(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.ROPE])
        state = make_state([player_one, player_two])

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert result is False


# ── Pending-bonus consumption (regression tests for the evaporation bug) ─────

class TestPendingBonusConsumption:

    def test_resource_discount_reduces_each_participant_cost(self):
        # LIGHT_A_FIRE needs 2 participants with 1 WOOD each. With a pending
        # WOOD discount the per-player cost is 0; neither participant should
        # lose wood from their hand.
        player_one = make_player(Character.COOK, [Resource.WOOD])
        player_two = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [player_one, player_two],
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert result is True
        assert player_one.resources == [Resource.WOOD]
        assert player_two.resources == [Resource.WOOD]

    def test_resource_discount_consumed_after_successful_attempt(self):
        player_one = make_player(Character.COOK, [Resource.WOOD])
        player_two = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [player_one, player_two],
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert state.pending_bonus is None

    def test_resource_discount_not_cleared_by_pre_compute_failure(self):
        # Attempt fails on wrong participant count before compute_per_player_requirements
        # runs. The bonus must remain available for the next attempt.
        player_one = make_player(Character.COOK, [])
        state = make_state(
            [player_one],
            pending_bonus = BonusEffect(resource_discount = { Resource.WOOD: 1 }),
        )

        result = resolve_mission(state, LIGHT_A_FIRE, [player_one], CALM_BREEZE)

        assert result is False
        assert state.pending_bonus is not None

    def test_resource_discount_any_reduces_complication_any_extra(self):
        # SLIPPERY_ROCKS charges 2 any-resource per participant. With a pending
        # resource_discount_any = 1 (e.g. from FORTIFY_THE_CAMP succeeding),
        # each participant pays only 1 any on top of the base WOOD cost.
        # Player_a holds exactly WOOD + 1 STONE; without the discount this hand
        # would fall 1 short of the SLIPPERY_ROCKS any_extra.
        player_a = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_b = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE])
        state = make_state(
            [player_a, player_b],
            pending_bonus = BonusEffect(resource_discount_any = 1),
        )

        result = resolve_mission(
            state,
            Mission.get(MissionName.LIGHT_A_FIRE),
            [player_a, player_b],
            ComplicationCard.get(ComplicationCardName.SLIPPERY_ROCKS),
        )

        assert result is True
        assert player_a.resources == []
        assert player_b.resources == []

    def test_resource_discount_any_consumed_after_successful_attempt(self):
        player_a = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_b = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE])
        state = make_state(
            [player_a, player_b],
            pending_bonus = BonusEffect(resource_discount_any = 1),
        )

        resolve_mission(
            state,
            Mission.get(MissionName.LIGHT_A_FIRE),
            [player_a, player_b],
            ComplicationCard.get(ComplicationCardName.SLIPPERY_ROCKS),
        )

        assert state.pending_bonus is None

    def test_resource_discount_any_preserved_on_pre_compute_failure(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            pending_bonus = BonusEffect(resource_discount_any = 1),
        )

        # Fails on wrong participant count before reaching the compute phase.
        resolve_mission(state, Mission.get(MissionName.LIGHT_A_FIRE), [player], CALM_BREEZE)

        assert state.pending_bonus is not None
        assert state.pending_bonus.resource_discount_any == 1

    def test_non_discount_bonus_is_not_cleared_by_resolve(self):
        player_one = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        player_two = make_player(Character.COOK, [Resource.WOOD, Resource.STONE])
        state = make_state(
            [player_one, player_two],
            pending_bonus = BonusEffect(negates_volcano_card = VolcanoCardName.RAIN_AND_MUD),
        )

        resolve_mission(state, LIGHT_A_FIRE, [player_one, player_two], CALM_BREEZE)

        assert state.pending_bonus is not None
        assert state.pending_bonus.negates_volcano_card == VolcanoCardName.RAIN_AND_MUD


# ── Per-player complication model ────────────────────────────────────────────

class TestPerPlayerComplicationModel:

    def test_mosquito_charges_each_participant_individually(self):
        # HUNT: 3 participants, base cost STONE:1 + ROPE:1 per player. Under
        # MOSQUITO_ATTACK each participant must also pay 1 extra ROPE. Total
        # rope consumed = 3 (up from 1 under the old pooled model).
        participants = [
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
        ]
        state = make_state(participants)

        result = resolve_mission(state, HUNT, participants, MOSQUITO_ATTACK)

        assert result is True
        assert state.resources_consumed.get(Resource.ROPE, 0) == 6
        for player in participants:
            assert player.resources == []

    def test_mosquito_fails_if_any_participant_short(self):
        # One participant lacks the extra ROPE that the complication charges.
        participants = [
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
        ]
        state = make_state(participants)

        result = resolve_mission(state, HUNT, participants, MOSQUITO_ATTACK)

        assert result is False

    def test_wet_wood_conditional_per_participant(self):
        participants = [
            make_player(Character.COOK, [Resource.WOOD, Resource.WOOD]),
            make_player(Character.COOK, [Resource.WOOD, Resource.WOOD]),
        ]
        state = make_state(participants)

        result = resolve_mission(state, LIGHT_A_FIRE, participants, WET_WOOD)

        assert result is True
        for player in participants:
            assert player.resources == []

    def test_wet_wood_not_charged_when_mission_lacks_wood(self):
        participants = [
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
        ]
        state = make_state(participants)

        result = resolve_mission(state, HUNT, participants, WET_WOOD)

        assert result is True
        for player in participants:
            assert player.resources == []

    def test_slippery_rocks_any_extra_per_participant(self):
        # LIGHT_A_FIRE: 2 participants at WOOD:1. SLIPPERY_ROCKS adds 2 any per
        # participant. Each must have WOOD plus 2 extra any-resources.
        participant_a = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.STONE])
        participant_b = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE, Resource.ROPE])
        state = make_state([participant_a, participant_b])

        result = resolve_mission(state, LIGHT_A_FIRE, [participant_a, participant_b], SLIPPERY_ROCKS)

        assert result is True
        assert participant_a.resources == []
        assert participant_b.resources == []

    def test_slippery_rocks_fails_if_one_participant_short_on_any(self):
        participant_a = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.STONE])
        participant_b = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE])
        state = make_state([participant_a, participant_b])

        result = resolve_mission(state, LIGHT_A_FIRE, [participant_a, participant_b], SLIPPERY_ROCKS)

        assert result is False

    def test_heat_and_thirst_one_any_per_participant(self):
        # HEAT_AND_THIRST: extra_per_participant=1. Each participant pays 1 any;
        # total consumed equals old pooled participants * 1.
        participants = [
            make_player(Character.COOK, [Resource.WOOD, Resource.STONE]),
            make_player(Character.COOK, [Resource.WOOD, Resource.STONE]),
        ]
        state = make_state(participants)

        result = resolve_mission(state, LIGHT_A_FIRE, participants, HEAT_AND_THIRST)

        assert result is True
        for player in participants:
            assert player.resources == []


# ── Per-participant volcano card extras ──────────────────────────────────────

class TestPerParticipantVolcanoExtras:

    def test_rain_and_mud_charges_each_participant_on_wood_mission(self):
        # LIGHT_A_FIRE: 2 participants at WOOD:1. RAIN_AND_MUD adds +2 WOOD per
        # participant (conditional on WOOD being in the base cost). Each player
        # needs WOOD:3 to succeed; total WOOD consumed = 6.
        participant_a = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD, Resource.WOOD])
        participant_b = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD, Resource.WOOD])
        state = make_state(
            [participant_a, participant_b],
            pending_volcano_card = VolcanoCardName.RAIN_AND_MUD,
        )

        result = resolve_mission(state, LIGHT_A_FIRE, [participant_a, participant_b], CALM_BREEZE)

        assert result is True
        assert state.resources_consumed.get(Resource.WOOD, 0) == 6
        assert participant_a.resources == []
        assert participant_b.resources == []

    def test_rain_and_mud_does_not_apply_to_non_wood_mission(self):
        participants = [
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
        ]
        state = make_state(participants, pending_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        result = resolve_mission(state, HUNT, participants, CALM_BREEZE)

        assert result is True
        for player in participants:
            assert player.resources == []

    def test_lava_flow_charges_rope_per_participant(self):
        # HUNT: 3 participants at STONE:1 + ROPE:1. LAVA_FLOW adds +1 ROPE per
        # participant unconditionally. Each player needs STONE:1 + ROPE:2.
        participants = [
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE]),
        ]
        state = make_state(participants, pending_volcano_card = VolcanoCardName.LAVA_FLOW)

        result = resolve_mission(state, HUNT, participants, CALM_BREEZE)

        assert result is True
        assert state.resources_consumed.get(Resource.ROPE, 0) == 6
        for player in participants:
            assert player.resources == []

    def test_pending_volcano_card_consumed_after_mission_with_extras(self):
        participant_a = make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE])
        participant_b = make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE])
        participant_c = make_player(Character.COOK, [Resource.STONE, Resource.ROPE, Resource.ROPE])
        state = make_state(
            [participant_a, participant_b, participant_c],
            pending_volcano_card = VolcanoCardName.LAVA_FLOW,
        )

        resolve_mission(state, HUNT, [participant_a, participant_b, participant_c], CALM_BREEZE)

        assert state.pending_volcano_card is None

    def test_pending_volcano_card_consumed_even_on_failure(self):
        # Attempt fails because participants lack the LAVA_FLOW extra; the card
        # is still consumed because the attempt reached the compute-and-pay phase.
        participants = [
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
            make_player(Character.COOK, [Resource.STONE, Resource.ROPE]),
        ]
        state = make_state(participants, pending_volcano_card = VolcanoCardName.LAVA_FLOW)

        result = resolve_mission(state, HUNT, participants, CALM_BREEZE)

        assert result is False
        assert state.pending_volcano_card is None

    def test_non_extras_volcano_card_is_not_consumed_by_resolve(self):
        # ASH_IN_THE_AIR is consumed by the exhaustion step, not by resolve_mission.
        player_a = make_player(Character.COOK, [Resource.WOOD])
        player_b = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [player_a, player_b],
            pending_volcano_card = VolcanoCardName.ASH_IN_THE_AIR,
        )

        resolve_mission(state, LIGHT_A_FIRE, [player_a, player_b], CALM_BREEZE)

        assert state.pending_volcano_card == VolcanoCardName.ASH_IN_THE_AIR
