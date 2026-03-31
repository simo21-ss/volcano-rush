import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName,
    ComplicationCardName, VolcanoCardName,
)
from simulation_engine.models.cards import BonusEffect
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.mechanics.exhaustion import refresh_exhaustion, apply_exhaustion, update_tool_repairs
from simulation_engine.mechanics.effects import apply_bonus


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

    def test_refresh_exhaustion_clears_when_past_due(self):
        player = make_player(Character.COOK, [])
        player.exhausted_until = 3
        player.is_exhausted = True
        state = make_state([player], round = 4)

        refresh_exhaustion(state)

        assert player.is_exhausted is False

    def test_update_tool_repairs_completes_repair(self):
        state = make_state([], round = 5)
        state.tools[Tool.KNIFE].damaged = True
        state.tools[Tool.KNIFE].repair_due = 5

        update_tool_repairs(state)

        assert state.tools[Tool.KNIFE].damaged is False
        assert state.tools[Tool.KNIFE].repair_due is None
        assert state.tool_repairs.get(Tool.KNIFE, 0) == 1


# ── apply_bonus ──────────────────────────────────────────────────────────────

class TestApplyBonus:

    def test_apply_bonus_boat_part(self):
        state = make_state([])
        bonus = BonusEffect(boat_part = True)

        apply_bonus(bonus, MissionName.CUT_THE_KEEL, state)

        assert MissionName.CUT_THE_KEEL in state.boat_parts_built

    def test_apply_bonus_repair_tool(self):
        state = make_state([])
        state.tools[Tool.KNIFE].damaged = True
        bonus = BonusEffect(repair_tool = True)

        apply_bonus(bonus, MissionName.GATHER_MATERIALS, state)

        assert state.tools[Tool.KNIFE].damaged is False
        assert state.tool_repairs.get(Tool.KNIFE, 0) == 1

    def test_apply_bonus_negate_volcano(self):
        state = make_state([], pending_volcano_card = VolcanoCardName.RAIN_AND_MUD)
        bonus = BonusEffect(negates_volcano_card = VolcanoCardName.RAIN_AND_MUD)

        apply_bonus(bonus, MissionName.BUILD_A_SHELTER, state)

        assert state.pending_volcano_card is None
