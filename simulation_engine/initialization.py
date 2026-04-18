import random

from .models import (
    Character, Resource, Tool, MissionType, MissionName, ComplicationCardName, VolcanoCardName,
    Player, GameState, ToolState, Mission,
)

_INITIAL_RESOURCES_PER_PLAYER = 3
_DECK_RESOURCE_COUNT = 20
_URGENT_VOLCANO_THRESHOLD = 4


def init_game(
        player_count: int,
        initial_resources_per_player: int = _INITIAL_RESOURCES_PER_PLAYER,
        deck_resource_count: int = _DECK_RESOURCE_COUNT,
        urgent_volcano_threshold: int = _URGENT_VOLCANO_THRESHOLD,
) -> GameState:
    # Prepare decks
    resource_deck = _prepare_resource_deck(deck_resource_count)
    complication_deck = _prepare_complication_deck()
    volcano_deck = _prepare_volcano_deck()

    # Prepare players
    players = _prepare_players(player_count, resource_deck, initial_resources_per_player)

    # Prepare missions
    boat_missions = _get_boat_missions(player_count)
    mission_pool = _prepare_mission_pool(boat_missions)
    active_missions = [mission_pool.pop() for _ in range(3)]

    # Prepare tools
    tools = { tool: ToolState() for tool in Tool }

    return GameState(
        players = players,
        active_missions = active_missions,
        resource_deck = resource_deck,
        complication_deck = complication_deck,
        volcano_deck = volcano_deck,
        tools = tools,
        boat_parts_required = len(boat_missions),
        mission_pool = mission_pool,
        urgent_volcano_threshold = urgent_volcano_threshold,
    )


def _prepare_resource_deck(deck_resource_count: int = 20) -> list[Resource]:
    resource_deck = ([Resource.WOOD] * deck_resource_count +
                     [Resource.STONE] * deck_resource_count +
                     [Resource.ROPE] * deck_resource_count)
    random.shuffle(resource_deck)

    return resource_deck


def _prepare_complication_deck() -> list[ComplicationCardName]:
    compilation_deck = list(ComplicationCardName)
    random.shuffle(compilation_deck)

    return compilation_deck


def _prepare_volcano_deck() -> list[VolcanoCardName]:
    eruption_card = VolcanoCardName.ERUPTION

    non_eruption = [v for v in VolcanoCardName if v != eruption_card]
    random.shuffle(non_eruption)

    volcano_deck = [eruption_card] + non_eruption

    return volcano_deck


def _prepare_players(player_count: int, resource_deck: list[Resource], initial_resources_per_player: int = 3) -> list[Player]:
    characters = _assign_characters(player_count)

    players = []
    for character in characters:
        player = Player(character)
        player.resources.extend(resource_deck.pop() for _ in range(initial_resources_per_player))
        players.append(player)

    return players


def _prepare_mission_pool(boat_missions: list[MissionName]) -> list[MissionName]:
    standard_missions = [n for n, m in Mission.catalog.items() if m.mission_type != MissionType.BOAT]
    mission_pool = standard_missions + boat_missions

    random.shuffle(mission_pool)

    return mission_pool


def _assign_characters(player_count: int) -> list[Character]:
    all_characters = list(Character)
    chosen_characters = all_characters

    if player_count > len(chosen_characters):
        extras = random.sample(
            [c for c in all_characters if c != Character.CRAFTSMAN],
            player_count - len(all_characters),
        )
        chosen_characters += extras

    random.shuffle(chosen_characters)

    return chosen_characters


def _get_boat_missions(player_count: int) -> list[MissionName]:
    all_boat_missions = [n for n, m in Mission.catalog.items() if m.mission_type == MissionType.BOAT]

    if player_count <= 6:
        excluded = { MissionName.MAKE_THE_SAIL, MissionName.FIT_THE_RUDDER }
    elif player_count <= 7:
        excluded = { MissionName.FIT_THE_RUDDER }
    else:
        excluded = set()

    return [n for n in all_boat_missions if n not in excluded]
