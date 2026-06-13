import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName,
    ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.bonus_effects import BonusEffect
from simulation_engine.models.state import Player, GameState, ToolState

from simulation_engine.mechanics.exhaustion import apply_exhaustion
from simulation_engine.mechanics.effects import apply_mission_bonus


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


# ── Exhaustion ───────────────────────────────────────────────────────────────

class TestExhaustion:

    def test_apply_exhaustion_sets_fields(self):
        player = make_player(Character.COOK, [])

        apply_exhaustion([player], current_round = 3, extra_rounds = 0)

        assert player.exhausted_until == 4
        assert player.is_exhausted is True

    def test_begin_round_clears_exhaustion_when_past_due(self):
        player = make_player(Character.COOK, [])
        player.exhausted_until = 3
        player.is_exhausted = True
        state = make_state([player], round = 3)

        state.begin_round()

        assert state.round == 4
        assert player.is_exhausted is False

    def test_begin_round_completes_tool_repair(self):
        player = make_player(Character.COOK, [])
        state = make_state([player], round = 4)
        state.tools[Tool.KNIFE].damaged = True
        state.tools[Tool.KNIFE].under_repair = True

        state.begin_round()

        assert state.round == 5
        assert state.tools[Tool.KNIFE].damaged is False
        assert state.tools[Tool.KNIFE].under_repair is False
        assert state.tool_repairs.get(Tool.KNIFE, 0) == 1


# ── apply_bonus ──────────────────────────────────────────────────────────────

class TestApplyBonus:

    def test_apply_bonus_boat_part(self):
        state = make_state([])
        bonus = BonusEffect(boat_part = True)

        apply_mission_bonus(bonus, MissionName.CUT_THE_KEEL, state, [])

        assert MissionName.CUT_THE_KEEL in state.boat_parts_built

    def test_apply_bonus_negate_volcano(self):
        state = make_state([], pending_volcano_cards = [VolcanoCardName.RAIN_AND_MUD])
        bonus = BonusEffect(negates_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        apply_mission_bonus(bonus, MissionName.BUILD_A_SHELTER, state, [])

        assert state.pending_volcano_cards == []

    def test_apply_bonus_participant_card_draws(self):
        player_one = make_player(Character.COOK, [])
        player_two = make_player(Character.GATHERER, [])
        state = make_state([player_one, player_two], resource_deck = [Resource.WOOD, Resource.STONE])
        bonus = BonusEffect(participant_card_draws = 1)

        apply_mission_bonus(bonus, MissionName.LIGHT_A_FIRE, state, [player_one, player_two])

        assert len(player_one.resources) == 1
        assert len(player_two.resources) == 1
        assert state.resource_deck == []

    def test_apply_bonus_empty_hand_card_draws(self):
        empty_player = make_player(Character.COOK, [])
        stocked_player = make_player(Character.GATHERER, [Resource.WOOD])
        state = make_state(
            [empty_player, stocked_player],
            resource_deck = [Resource.STONE, Resource.ROPE],
        )
        bonus = BonusEffect(empty_hand_card_draws = 1)

        apply_mission_bonus(bonus, MissionName.FORTIFY_THE_CAMP, state, [])

        assert len(empty_player.resources) == 1
        assert stocked_player.resources == [Resource.WOOD]
        assert len(state.resource_deck) == 1
