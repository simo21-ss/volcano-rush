import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionType, MissionName,
    ComplicationCardName, VolcanoCardName, BOAT_PART_ORDER,
)
from simulation_engine.models.missions import Mission
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.actions import PlayerAction
from simulation_engine.agents.mission_selection import decide_mission_action, vote_for_mission
from simulation_engine.agents.participant_selection import active_player_select_participants
from simulation_engine.engine.round import run_round
from simulation_engine.engine.phases import apply_exhaustion_step


# ── Constants ────────────────────────────────────────────────────────────────

LIGHT_A_FIRE = Mission.get(MissionName.LIGHT_A_FIRE)
HUNT = Mission.get(MissionName.HUNT)
FETCH_WATER = Mission.get(MissionName.FETCH_WATER)
CUT_THE_KEEL = Mission.get(MissionName.CUT_THE_KEEL)
ASSEMBLE_THE_HULL = Mission.get(MissionName.ASSEMBLE_THE_HULL)
RAISE_THE_MAST = Mission.get(MissionName.RAISE_THE_MAST)
GATHER_MATERIALS = Mission.get(MissionName.GATHER_MATERIALS)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_player(character: Character, resources: list[Resource]) -> Player:
    return Player(character = character, resources = list(resources))


def make_state(players: list[Player], **overrides) -> GameState:
    defaults = {
        "players": players,
        "active_missions": [],
        "resource_deck": [Resource.WOOD, Resource.STONE, Resource.ROPE] * 20,
        "complication_deck": [ComplicationCardName.CALM_BREEZE] * 10,
        "volcano_deck": [VolcanoCardName.ERUPTION] + [VolcanoCardName.ASH_IN_THE_AIR] * 10,
        "tools": { Tool.KNIFE: ToolState(), Tool.VESSEL: ToolState() },
        "boat_parts_required": 4,
    }
    defaults.update(overrides)
    return GameState(**defaults)


# ── vote_for_mission filters and preferences ─────────────────────────────────

class TestVoteForMission:

    def test_panic_filters_boat_missions_out(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state(
            [player],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )

        vote = vote_for_mission(player, state)

        assert vote == MissionName.LIGHT_A_FIRE

    def test_panic_returns_none_when_only_boat_missions_are_active(self):
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state(
            [player],
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )

        assert vote_for_mission(player, state) is None

    def test_urgent_volcano_picks_next_needed_boat_part(self):
        random.seed(0)
        players = [
            make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]),
            make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]),
            make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]),
        ]
        state = make_state(
            players,
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.ASSEMBLE_THE_HULL, MissionName.CUT_THE_KEEL],
            volcano_deck = [VolcanoCardName.ERUPTION, VolcanoCardName.ASH_IN_THE_AIR],
            urgent_volcano_threshold = 4,
        )

        vote = vote_for_mission(players[0], state)

        # BOAT_PART_ORDER starts with CUT_THE_KEEL, which is among the active
        # feasible boat parts, so that should be chosen first.
        assert vote == MissionName.CUT_THE_KEEL
        assert BOAT_PART_ORDER[0] == MissionName.CUT_THE_KEEL

    def test_falls_back_to_unfiltered_active_missions_when_none_feasible(self):
        random.seed(0)
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT],
        )

        vote = vote_for_mission(player, state)

        assert vote in { MissionName.LIGHT_A_FIRE, MissionName.HUNT }


# ── decide_mission_action (shuffle branch) ───────────────────────────────────

class TestDecideMissionAction:

    def test_shuffle_requested_when_panic_and_all_boats_with_resource_to_spend(self):
        player = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [player],
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )

        assert decide_mission_action(player, state) == PlayerAction.SHUFFLE_MISSIONS

    def test_no_shuffle_when_any_non_boat_mission_is_active(self):
        player = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [player],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.CUT_THE_KEEL, MissionName.RAISE_THE_MAST],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )

        assert decide_mission_action(player, state) is None

    def test_shuffle_requested_when_wrong_boat_parts_and_resource_to_spend(self):
        player = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [player],
            active_missions = [MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST, MissionName.MAKE_THE_SAIL],
            boat_parts_built = set(),
        )

        # CUT_THE_KEEL is the next-needed part per BOAT_PART_ORDER but it's not
        # in the active missions; shuffling is cheaper than building out of order.
        assert decide_mission_action(player, state) == PlayerAction.SHUFFLE_MISSIONS

    def test_no_shuffle_when_active_player_has_no_resource(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            active_missions = [MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST, MissionName.MAKE_THE_SAIL],
        )

        assert decide_mission_action(player, state) is None


# ── active_player_select_participants ────────────────────────────────────────

class TestActivePlayerSelectParticipants:

    def test_active_player_prepended_when_affordable(self):
        random.seed(0)
        active_player = make_player(Character.COOK, [Resource.WOOD])
        others = [
            make_player(Character.COOK, [Resource.WOOD]),
            make_player(Character.COOK, [Resource.WOOD]),
        ]
        state = make_state([active_player] + others)

        participants = active_player_select_participants(active_player, LIGHT_A_FIRE, state)

        assert participants[0] is active_player
        assert len(participants) == LIGHT_A_FIRE.players_count

    def test_active_player_not_prepended_when_unaffordable(self):
        random.seed(0)
        active_player = make_player(Character.COOK, [Resource.STONE])
        others = [
            make_player(Character.COOK, [Resource.WOOD]),
            make_player(Character.COOK, [Resource.WOOD]),
        ]
        state = make_state([active_player] + others)

        participants = active_player_select_participants(active_player, LIGHT_A_FIRE, state)

        assert active_player not in participants
        assert len(participants) == LIGHT_A_FIRE.players_count

    def test_craftsman_penalised_when_tool_damaged(self):
        random.seed(0)
        active_player = make_player(Character.COOK, [Resource.WOOD])
        craftsman = make_player(Character.CRAFTSMAN, [Resource.WOOD])
        other_affordable = make_player(Character.COOK, [Resource.WOOD])
        state = make_state([active_player, craftsman, other_affordable])
        state.tools[Tool.KNIFE].damaged = True

        participants = active_player_select_participants(active_player, LIGHT_A_FIRE, state)

        # Active player + 1 other; the Craftsman should be de-prioritised so the
        # other cook is chosen instead.
        assert craftsman not in participants
        assert other_affordable in participants


# ── run_round branches ───────────────────────────────────────────────────────

class TestRunRound:

    def test_shuffle_branch_runs_without_error_and_rotates_active_player(self):
        random.seed(0)
        active_player = make_player(Character.COOK, [Resource.WOOD])
        other = make_player(Character.COOK, [Resource.WOOD])
        state = make_state(
            [active_player, other],
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST],
            mission_pool = [MissionName.LIGHT_A_FIRE, MissionName.HUNT],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )

        outcome = run_round(state)

        assert outcome is None
        # Rotated active player -> index 1.
        assert state.active_player_index == 1
        # Active player spent a resource to shuffle.
        assert active_player.resources == []

    def test_forfeit_branch_when_panic_and_no_resources(self):
        random.seed(0)
        active_player = make_player(Character.COOK, [])
        other = make_player(Character.COOK, [])
        state = make_state(
            [active_player, other],
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST],
            mission_pool = [],
            pending_volcano_cards = [VolcanoCardName.PANIC],
            volcano_deck = [VolcanoCardName.ERUPTION],
        )

        outcome = run_round(state)

        # Forfeit round draws a volcano card; the deck is rigged to ERUPTION so
        # the game ends immediately.
        from simulation_engine.models.enums import GameOutcome
        assert outcome == GameOutcome.LOSS

    def test_mission_branch_success_rotates_and_replaces_mission(self):
        random.seed(0)
        active_player = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD])
        other = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD])
        third = make_player(Character.COOK, [Resource.WOOD, Resource.WOOD])
        state = make_state(
            [active_player, other, third],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT, MissionName.FETCH_WATER],
            mission_pool = [MissionName.GATHER_MATERIALS],
        )

        outcome = run_round(state)

        assert outcome is None
        # LIGHT_A_FIRE should have resolved successfully; it's removed and a new
        # mission drawn.
        assert MissionName.LIGHT_A_FIRE not in state.active_missions
        assert state.active_player_index == 1


# ── end-of-round housekeeping ────────────────────────────────────────────────

class TestEndRound:

    def test_end_round_consumes_pending_panic(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )

        state.end_round()

        assert state.pending_volcano_cards == []

    def test_end_round_preserves_non_panic_pending_volcano(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            pending_volcano_cards = [VolcanoCardName.RAIN_AND_MUD],
        )

        state.end_round()

        assert state.pending_volcano_cards == [VolcanoCardName.RAIN_AND_MUD]

    def test_end_round_replaces_completed_mission_with_a_pool_draw(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT, MissionName.FETCH_WATER],
            mission_pool = [MissionName.GATHER_MATERIALS],
        )

        state.end_round(completed_mission = MissionName.LIGHT_A_FIRE)

        assert MissionName.LIGHT_A_FIRE not in state.active_missions
        assert MissionName.GATHER_MATERIALS in state.active_missions
        assert state.mission_pool == []

    def test_end_round_without_completed_mission_leaves_active_untouched(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT, MissionName.FETCH_WATER],
            mission_pool = [MissionName.GATHER_MATERIALS],
        )

        state.end_round()

        assert MissionName.LIGHT_A_FIRE in state.active_missions
        assert MissionName.GATHER_MATERIALS not in state.active_missions

    def test_end_round_with_empty_pool_leaves_active_missions_short(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT, MissionName.FETCH_WATER],
            mission_pool = [],
        )

        state.end_round(completed_mission = MissionName.LIGHT_A_FIRE)

        assert len(state.active_missions) == 2
        assert MissionName.LIGHT_A_FIRE not in state.active_missions

    def test_end_round_returns_win_when_boat_complete(self):
        from simulation_engine.models.enums import GameOutcome
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            boat_parts_required = 3,
            boat_parts_built = { MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST },
        )

        assert state.end_round() == GameOutcome.WIN


# ── Ash-in-the-air extra exhaustion ──────────────────────────────────────────

class TestApplyExhaustionStep:

    def test_ash_in_the_air_adds_extra_exhaustion_rounds(self):
        player = make_player(Character.COOK, [])
        state = make_state(
            [player],
            round = 3,
            pending_volcano_cards = [VolcanoCardName.ASH_IN_THE_AIR],
        )

        apply_exhaustion_step(state, [player])

        assert player.exhausted_until == 3 + 1 + 1
        # The card is consumed.
        assert state.pending_volcano_cards == []

    def test_skip_exhaustion_flag_skips_exhaustion_and_is_consumed(self):
        player = make_player(Character.COOK, [])
        state = make_state([player], round = 3, skip_exhaustion = True)

        apply_exhaustion_step(state, [player])

        assert player.is_exhausted is False
        assert player.exhausted_until == 0
        assert state.skip_exhaustion is False
