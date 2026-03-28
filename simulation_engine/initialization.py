import random

from .models import (
    Character, Resource, Tool, MissionType, MissionName, ComplicationCardName, VolcanoCardName,
    Player, GameState, ToolState, Mission,
)


def prepare_resource_deck(deck_resource_count: int = 20) -> list[Resource]:
    resource_deck = ([Resource.WOOD] * deck_resource_count + [Resource.STONE] * deck_resource_count + [Resource.ROPE] * deck_resource_count)
    random.shuffle(resource_deck)

    return resource_deck


def assign_characters(player_count: int) -> list[Character]:
    required_character = Character.CRAFTSMAN
    all_characters = list(Character)
    all_characters_count = len(all_characters)

    if player_count < all_characters_count:
        others = [c for c in all_characters if c != required_character]
        chosen = random.sample(others, player_count - 1)
        characters = [required_character] + chosen
    elif player_count == all_characters_count:
        characters = all_characters
    else:
        base_characters = random.sample(all_characters, all_characters_count)
        extras = random.sample(all_characters, player_count - all_characters_count)
        characters = base_characters + extras

    random.shuffle(characters)

    return characters


def prepare_players(player_count: int, resource_deck: list[Resource], initial_resources_per_player: int = 3) -> list[Player]:
    characters = assign_characters(player_count)

    players = []
    for char in characters:
        player = Player(character = char)
        player.resources.extend(resource_deck.pop() for _ in range(initial_resources_per_player))
        players.append(player)

    return players


def get_boat_missions(player_count: int) -> list[MissionName]:
    all_characters_count = len(list(Character))
    extra_mission = MissionName.FIT_THE_RUDDER

    base_boat_missions = [n for n, m in Mission.catalog.items()
            if m.mission_type == MissionType.BOAT and n != extra_mission]

    if player_count < all_characters_count:
        return random.sample(base_boat_missions, 2)
    elif player_count == all_characters_count:
        return list(base_boat_missions)
    else:
        return list(base_boat_missions) + [extra_mission]


def get_mission_pool(player_count: int) -> list[MissionName]:
    boat_missions = get_boat_missions(player_count)
    standard_missions = [n for n, m in Mission.catalog.items() if m.mission_type != MissionType.BOAT]
    mission_pool = standard_missions + boat_missions

    random.shuffle(mission_pool)

    return mission_pool


def prepare_complication_deck() -> list[ComplicationCardName]:
    compilation_deck = list(ComplicationCardName)
    random.shuffle(compilation_deck)

    return compilation_deck


def prepare_volcano_deck() -> list[VolcanoCardName]:
    eruption_card = VolcanoCardName.ERUPTION

    non_eruption = [v for v in VolcanoCardName if v != eruption_card]
    random.shuffle(non_eruption)

    volcano_deck = [eruption_card] + non_eruption

    return volcano_deck


def init_game(
    player_count:                 int,
    initial_resources_per_player: int = 3,
    deck_resource_count:          int = 20,
    urgent_volcano_threshold:     int = 4,
) -> GameState:
    resource_deck = prepare_resource_deck(deck_resource_count = deck_resource_count)

    players = prepare_players(player_count, resource_deck, initial_resources_per_player = initial_resources_per_player)

    mission_pool = get_mission_pool(player_count)
    active_missions = [mission_pool.pop() for _ in range(3)]

    volcano_deck = prepare_volcano_deck()
    complication_deck = prepare_complication_deck()

    tools = {tool: ToolState() for tool in Tool}

    boat_missions = get_boat_missions(player_count)
    boat_parts_required = len(boat_missions)

    return GameState(
        players                  = players,
        active_missions          = active_missions,
        resource_deck            = resource_deck,
        complication_deck        = complication_deck,
        volcano_deck             = volcano_deck,
        tools                    = tools,
        boat_parts_required      = boat_parts_required,
        mission_pool             = mission_pool,
        urgent_volcano_threshold = urgent_volcano_threshold,
    )
