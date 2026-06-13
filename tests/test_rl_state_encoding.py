import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import (
    Character, Resource, Tool, MissionName, VolcanoCardName,
)
from simulation_engine.models.missions import Mission
from simulation_engine.models.state import Player, GameState, ToolState
from simulation_engine.characters import get_strategy
from simulation_engine.rl.state_encoding import (
    MissionStateEncoder, ParticipantStateEncoder, bucket_index, next_needed_boat_part,
)


HUNT = Mission.get(MissionName.HUNT)
CUT_THE_KEEL = Mission.get(MissionName.CUT_THE_KEEL)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_player(character: Character, resources: list[Resource], score: int = 0) -> Player:
    return Player(character = character, resources = list(resources), score = score)


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


# ── bucket_index ───────────────────────────────────────────────────────────────

class TestBucketIndex:

    def test_boundaries(self):
        edges = (4, 8, 12)
        assert bucket_index(0, edges) == 0
        assert bucket_index(4, edges) == 0
        assert bucket_index(5, edges) == 1
        assert bucket_index(8, edges) == 1
        assert bucket_index(9, edges) == 2
        assert bucket_index(12, edges) == 2
        assert bucket_index(13, edges) == 3


# ── MissionStateEncoder ────────────────────────────────────────────────────────

class TestMissionStateEncoder:

    def test_cardinality_is_4608(self):
        assert MissionStateEncoder().cardinality() == 4608

    def test_key_has_seven_integer_features_within_bounds(self):
        encoder = MissionStateEncoder()
        player = make_player(Character.COOK, [Resource.WOOD, Resource.STONE, Resource.ROPE])
        state = make_state(
            [player] * 6,
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT, MissionName.FETCH_WATER],
        )
        key = encoder.encode(player, state)
        assert isinstance(key, tuple)
        assert len(key) == 7
        urgency, boat_progress, panic, next_boat_status, any_feasible_boat, bitmask, can_afford_any = key
        assert 0 <= urgency <= 3
        assert 0 <= boat_progress <= 5
        assert panic in (0, 1)
        assert next_boat_status in (0, 1, 2)
        assert any_feasible_boat in (0, 1)
        assert 0 <= bitmask <= 7
        assert can_afford_any in (0, 1)

    def test_urgency_bucket_tracks_volcano_deck_length(self):
        encoder = MissionStateEncoder()
        player = make_player(Character.COOK, [Resource.WOOD])
        urgent_state = make_state([player], volcano_deck = [VolcanoCardName.ERUPTION] * 3)
        calm_state = make_state([player], volcano_deck = [VolcanoCardName.ERUPTION] * 13)
        assert encoder.encode(player, urgent_state)[0] == 0
        assert encoder.encode(player, calm_state)[0] == 3

    def test_panic_flag_reflects_pending_cards(self):
        encoder = MissionStateEncoder()
        player = make_player(Character.COOK, [Resource.WOOD])
        without_panic = make_state([player], active_missions = [MissionName.HUNT])
        with_panic = make_state(
            [player],
            active_missions = [MissionName.HUNT],
            pending_volcano_cards = [VolcanoCardName.PANIC],
        )
        assert encoder.encode(player, without_panic)[2] == 0
        assert encoder.encode(player, with_panic)[2] == 1

    def test_next_needed_boat_status_absent_present_infeasible_and_feasible(self):
        encoder = MissionStateEncoder()
        crew = [make_player(Character.COOK, [Resource.WOOD, Resource.ROPE]) for _ in range(6)]

        # Absent: the next-needed boat part (Cut the Keel) is not on offer.
        absent_state = make_state(
            crew,
            active_missions = [MissionName.LIGHT_A_FIRE, MissionName.HUNT, MissionName.FETCH_WATER],
        )
        assert next_needed_boat_part(absent_state) == MissionName.CUT_THE_KEEL
        assert encoder.encode(crew[0], absent_state)[3] == 0

        # Present and feasible: Cut the Keel on offer, crew can pay, Knife intact.
        feasible_state = make_state(
            crew,
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.HUNT, MissionName.FETCH_WATER],
        )
        assert encoder.encode(crew[0], feasible_state)[3] == 2

        # Present but infeasible: same offer, but the required Knife is damaged.
        infeasible_state = make_state(
            crew,
            active_missions = [MissionName.CUT_THE_KEEL, MissionName.HUNT, MissionName.FETCH_WATER],
            tools = { Tool.KNIFE: ToolState(damaged = True), Tool.VESSEL: ToolState() },
        )
        assert encoder.encode(crew[0], infeasible_state)[3] == 1

    def test_abstraction_collapses_unmodeled_dimensions(self):
        encoder = MissionStateEncoder()
        player = make_player(Character.COOK, [Resource.WOOD, Resource.ROPE])
        base_state = make_state([player] * 6, active_missions = [MissionName.HUNT, MissionName.FETCH_WATER, MissionName.CUT_THE_KEEL])
        other_state = make_state([player] * 6, active_missions = [MissionName.HUNT, MissionName.FETCH_WATER, MissionName.CUT_THE_KEEL])
        # round and active_player_index are not part of the abstraction.
        other_state.round = 57
        other_state.active_player_index = 3
        assert encoder.encode(player, base_state) == encoder.encode(player, other_state)


# ── ParticipantStateEncoder ──────────────────────────────────────────────────

class TestParticipantStateEncoder:

    def test_cardinality_is_144(self):
        assert ParticipantStateEncoder().cardinality() == 144

    def test_afford_index_orders_cannot_exact_surplus(self):
        encoder = ParticipantStateEncoder()
        active_player = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE])

        cannot = make_player(Character.SAILOR, [])
        exact = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE])
        surplus = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE, Resource.WOOD, Resource.ROPE])
        state = make_state([active_player, cannot, exact, surplus])

        assert encoder.encode(cannot, active_player, CUT_THE_KEEL, state)[0] == 0
        assert encoder.encode(exact, active_player, CUT_THE_KEEL, state)[0] == 1
        assert encoder.encode(surplus, active_player, CUT_THE_KEEL, state)[0] == 2

    def test_ability_feature_matches_character_strategy(self):
        encoder = ParticipantStateEncoder()
        active_player = make_player(Character.SAILOR, [Resource.STONE, Resource.ROPE])
        cook = make_player(Character.COOK, [Resource.STONE, Resource.ROPE])
        state = make_state([active_player, cook])
        expected = 1 if get_strategy(Character.COOK).has_active_ability_on(HUNT) else 0
        assert encoder.encode(cook, active_player, HUNT, state)[1] == expected

    def test_craftsman_repair_feature(self):
        encoder = ParticipantStateEncoder()
        active_player = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE])
        craftsman = make_player(Character.CRAFTSMAN, [Resource.WOOD, Resource.ROPE])

        intact = make_state([active_player, craftsman])
        assert encoder.encode(craftsman, active_player, CUT_THE_KEEL, intact)[2] == 0

        damaged = make_state(
            [active_player, craftsman],
            tools = { Tool.KNIFE: ToolState(damaged = True), Tool.VESSEL: ToolState() },
        )
        assert encoder.encode(craftsman, active_player, CUT_THE_KEEL, damaged)[2] == 1
        # A non-Craftsman is unaffected by a damaged tool.
        non_craftsman = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE])
        assert encoder.encode(non_craftsman, active_player, CUT_THE_KEEL, damaged)[2] == 0

    def test_lead_bucket_and_boat_and_active_features(self):
        encoder = ParticipantStateEncoder()
        active_player = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE], score = 5)

        behind = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE], score = 5)
        slightly_ahead = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE], score = 7)
        far_ahead = make_player(Character.SAILOR, [Resource.WOOD, Resource.ROPE], score = 12)
        state = make_state([active_player, behind, slightly_ahead, far_ahead])

        assert encoder.encode(behind, active_player, CUT_THE_KEEL, state)[3] == 0
        assert encoder.encode(slightly_ahead, active_player, CUT_THE_KEEL, state)[3] == 1
        assert encoder.encode(far_ahead, active_player, CUT_THE_KEEL, state)[3] == 2

        # mission_is_boat
        assert encoder.encode(behind, active_player, CUT_THE_KEEL, state)[4] == 1
        assert encoder.encode(behind, active_player, HUNT, state)[4] == 0

        # is_active_player
        assert encoder.encode(active_player, active_player, CUT_THE_KEEL, state)[5] == 1
        assert encoder.encode(behind, active_player, CUT_THE_KEEL, state)[5] == 0
