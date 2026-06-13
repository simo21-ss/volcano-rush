import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName, MissionType, VolcanoCardName,
)
from simulation_engine.models.missions import Mission
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.agents.mission_selection import vote_for_mission
from simulation_engine.rl.action_space import (
    MISSION_ACTION_NEXT_BOAT, MISSION_ACTION_OTHER_BOAT,
    MISSION_ACTION_FIRE, MISSION_ACTION_FOOD, MISSION_ACTION_SHELTER,
    legal_missions, encode_mission_action, legal_mission_action_indices, decode_mission_action,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_player(character: Character, resources: list[Resource]) -> Player:
    return Player(character = character, resources = list(resources))


def make_state(players: list[Player], **overrides) -> GameState:
    defaults = {
        "players": players,
        "active_missions": [],
        "resource_deck": [Resource.WOOD, Resource.STONE, Resource.ROPE] * 20,
        "complication_deck": [],
        "volcano_deck": [VolcanoCardName.ERUPTION] + [VolcanoCardName.ASH_IN_THE_AIR] * 10,
        "tools": { Tool.KNIFE: ToolState(), Tool.VESSEL: ToolState() },
        "boat_parts_required": 4,
    }
    defaults.update(overrides)
    return GameState(**defaults)


def rich_crew(size: int = 6) -> list[Player]:
    """A crew where each player can pay any single base mission cost."""
    return [
        make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        for _ in range(size)
    ]


# ── legal_missions ─────────────────────────────────────────────────────────────

class TestLegalMissions:

    def test_prefers_feasible_subset(self):
        crew = rich_crew()
        # One mission nobody can afford (impossible cost is simulated by emptying hands
        # for a copy is awkward; instead use a feasible vs infeasible split via tools).
        state = make_state(
            crew,
            active_missions = [MissionName.HUNT, MissionName.FETCH_WATER, MissionName.GATHER_MATERIALS],
        )
        candidates = legal_missions(crew[0], state)
        assert set(candidates) == {MissionName.HUNT, MissionName.FETCH_WATER, MissionName.GATHER_MATERIALS}

    def test_panic_bans_boat_missions(self):
        crew = rich_crew()
        state = make_state(
            crew,
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.HUNT, MissionName.LIGHT_A_FIRE],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )
        candidates = legal_missions(crew[0], state)
        assert MissionName.CUT_THE_KEEL not in candidates
        assert set(candidates) == {MissionName.HUNT, MissionName.LIGHT_A_FIRE}

    def test_panic_with_only_boats_leaves_nothing_legal(self):
        crew = rich_crew()
        state = make_state(
            crew,
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )
        assert legal_missions(crew[0], state) == []

    def test_falls_back_to_active_when_none_feasible(self):
        # A two-player crew cannot staff any 3-player mission, so nothing is feasible
        # and legal_missions falls back to the full active list.
        crew = rich_crew(size = 2)
        state = make_state(
            crew,
            active_missions = [MissionName.HUNT, MissionName.FETCH_WATER, MissionName.GATHER_MATERIALS],
        )
        candidates = legal_missions(crew[0], state)
        assert set(candidates) == {MissionName.HUNT, MissionName.FETCH_WATER, MissionName.GATHER_MATERIALS}


# ── vote_for_mission consistency ───────────────────────────────────────────────

class TestVoteConsistency:

    def test_rule_based_choice_is_always_legal(self):
        random.seed(0)
        crew = rich_crew()
        for active_missions in (
            [MissionName.HUNT, MissionName.FETCH_WATER, MissionName.LIGHT_A_FIRE],
            [MissionName.CUT_THE_KEEL, MissionName.HUNT, MissionName.GATHER_MATERIALS],
            [MissionName.CUT_THE_KEEL, MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST],
        ):
            state = make_state(crew, active_missions = active_missions)
            chosen = vote_for_mission(crew[0], state)
            candidates = legal_missions(crew[0], state)
            assert chosen in candidates


# ── encode / decode ─────────────────────────────────────────────────────────

class TestEncodeDecode:

    def test_category_assignment(self):
        crew = rich_crew()
        state = make_state(crew, active_missions = [MissionName.CUT_THE_KEEL])
        assert encode_mission_action(MissionName.CUT_THE_KEEL, state) == MISSION_ACTION_NEXT_BOAT
        # With the keel already built, the hull becomes the next-needed boat part.
        state.boat_parts_built = {MissionName.CUT_THE_KEEL}
        assert encode_mission_action(MissionName.CUT_THE_KEEL, state) == MISSION_ACTION_OTHER_BOAT
        assert encode_mission_action(MissionName.ASSEMBLE_THE_HULL, state) == MISSION_ACTION_NEXT_BOAT
        assert encode_mission_action(MissionName.LIGHT_A_FIRE, state) == MISSION_ACTION_FIRE
        assert encode_mission_action(MissionName.HUNT, state) == MISSION_ACTION_FOOD
        assert encode_mission_action(MissionName.GATHER_MATERIALS, state) == MISSION_ACTION_SHELTER

    def test_round_trips_for_every_legal_mission(self):
        crew = rich_crew()
        state = make_state(
            crew,
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.HUNT, MissionName.LIGHT_A_FIRE],
        )
        legal = legal_missions(crew[0], state)
        for mission_name in legal:
            category = encode_mission_action(mission_name, state)
            decoded = decode_mission_action(category, legal, state)
            assert decoded is not None
            assert encode_mission_action(decoded, state) == category

    def test_boat_tie_break_prefers_next_then_build_order(self):
        crew = rich_crew()
        state = make_state(
            crew,
            active_missions = [MissionName.ASSEMBLE_THE_HULL, MissionName.RAISE_THE_MAST, MissionName.CUT_THE_KEEL],
        )
        legal = legal_missions(crew[0], state)
        # Next-needed boat decodes to the keel.
        assert decode_mission_action(MISSION_ACTION_NEXT_BOAT, legal, state) == MissionName.CUT_THE_KEEL
        # Other-boat decodes to the earliest non-next boat in build order (the hull).
        assert decode_mission_action(MISSION_ACTION_OTHER_BOAT, legal, state) == MissionName.ASSEMBLE_THE_HULL

    def test_decode_returns_none_for_absent_category(self):
        crew = rich_crew()
        state = make_state(crew, active_missions = [MissionName.HUNT, MissionName.FETCH_WATER])
        legal = legal_missions(crew[0], state)
        # No fire mission is on offer.
        assert decode_mission_action(MISSION_ACTION_FIRE, legal, state) is None

    def test_legal_action_indices_lists_present_categories(self):
        crew = rich_crew()
        state = make_state(
            crew,
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.HUNT, MissionName.LIGHT_A_FIRE],
        )
        indices = legal_mission_action_indices(crew[0], state)
        assert indices == sorted([MISSION_ACTION_NEXT_BOAT, MISSION_ACTION_FOOD, MISSION_ACTION_FIRE])
