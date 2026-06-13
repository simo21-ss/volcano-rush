import sys
import os
import random
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation_engine.models.enums import GameOutcome, MissionName
from simulation_engine.models.state import Player, GameState
from simulation_engine.models.missions import Mission
from simulation_engine.engine.game import run_game, run_scenario


# Reference statistics captured on the unmodified engine (before the selector
# hook was added), for run_scenario(player_count = 7, n_games = 200, base_seed = 42).
# Because base_seed is fixed, the default (no-selector) path must reproduce these
# exactly. Any drift means the hook changed behaviour and is a bug.
REFERENCE_PLAYER_COUNT = 7
REFERENCE_N_GAMES = 200
REFERENCE_BASE_SEED = 42
REFERENCE_WINS = 70
REFERENCE_TOTAL_ROUNDS = 3544
REFERENCE_TOTAL_BOAT_PARTS = 584
REFERENCE_TOTAL_SCORE_BY_CHARACTER_NAME = {
    "BUILDER": 1318,
    "COOK": 1397,
    "CRAFTSMAN": 1360,
    "FIRE_STARTER": 1323,
    "GATHERER": 1315,
    "SAILOR": 1208,
}


# ── Trivial injected selectors (used to prove the hook is wired) ───────────────

def always_forfeit(player: Player, state: GameState) -> Optional[MissionName]:
    """A mission selector that never picks a mission, forfeiting every round."""
    return None


def no_participants(active_player: Player, mission: Mission, state: GameState) -> list[Player]:
    """A participant selector that staffs no one, so missions cannot succeed."""
    return []


# ── Backward compatibility (the bit-identical gate) ────────────────────────────

class TestDefaultPathIsBitIdentical:

    def test_scenario_matches_captured_reference(self):
        records = run_scenario(
            player_count = REFERENCE_PLAYER_COUNT,
            n_games = REFERENCE_N_GAMES,
            base_seed = REFERENCE_BASE_SEED,
        )

        wins = sum(1 for record in records if record.outcome == GameOutcome.WIN)
        total_rounds = sum(record.rounds_played for record in records)
        total_boat_parts = sum(record.boat_parts_built for record in records)

        assert wins == REFERENCE_WINS
        assert total_rounds == REFERENCE_TOTAL_ROUNDS
        assert total_boat_parts == REFERENCE_TOTAL_BOAT_PARTS

        total_score_by_character_name = {}
        for record in records:
            for character, score in record.final_scores.items():
                total_score_by_character_name[character.name] = (
                    total_score_by_character_name.get(character.name, 0) + score
                )
        assert total_score_by_character_name == REFERENCE_TOTAL_SCORE_BY_CHARACTER_NAME

    def test_explicit_none_selectors_match_no_argument_default(self):
        random.seed(123)
        record_default = run_game(player_count = 7)

        random.seed(123)
        record_explicit_none = run_game(
            player_count = 7,
            mission_selector = None,
            participant_selector = None,
        )

        assert record_default.outcome == record_explicit_none.outcome
        assert record_default.rounds_played == record_explicit_none.rounds_played
        assert record_default.boat_parts_built == record_explicit_none.boat_parts_built
        assert record_default.final_scores == record_explicit_none.final_scores


# ── Injection actually changes behaviour (proves the hook is wired) ────────────

class TestInjectedSelectorsChangeOutcomes:

    def test_forfeit_mission_selector_wins_nothing(self):
        baseline = run_scenario(player_count = 7, n_games = 50, base_seed = 42)
        baseline_wins = sum(1 for record in baseline if record.outcome == GameOutcome.WIN)

        forfeited = run_scenario(
            player_count = 7,
            n_games = 50,
            base_seed = 42,
            mission_selector = always_forfeit,
        )
        forfeited_wins = sum(1 for record in forfeited if record.outcome == GameOutcome.WIN)

        assert baseline_wins > 0
        assert forfeited_wins == 0
        assert forfeited_wins != baseline_wins

    def test_empty_participant_selector_wins_nothing(self):
        baseline = run_scenario(player_count = 7, n_games = 50, base_seed = 42)
        baseline_wins = sum(1 for record in baseline if record.outcome == GameOutcome.WIN)

        unstaffed = run_scenario(
            player_count = 7,
            n_games = 50,
            base_seed = 42,
            participant_selector = no_participants,
        )
        unstaffed_wins = sum(1 for record in unstaffed if record.outcome == GameOutcome.WIN)

        assert baseline_wins > 0
        assert unstaffed_wins == 0
