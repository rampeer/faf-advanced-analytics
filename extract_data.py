from __future__ import annotations

import io
from dataclasses import dataclass
from json import JSONDecodeError
import logging

from src.faf_replay import parse_replay, ParsedReplayData
from src.storage import has_metadata, get_metadata, write_metadata, list_replays, get_replay

METADATA_VERSION = 1


@dataclass
class ReplayPlayerMetadata:
    player_id: str
    nickname: str
    clan: str
    country: str

    rating_mean: float
    rating_std: float
    rating: float

    faction: int
    team: int


@dataclass
class ReplayMetadata:
    title: str
    replay_id: str

    launched_at_ts: int
    duration: float
    map: str
    type: str
    players: list[ReplayPlayerMetadata]


def ensure_str(str_or_bytes: str | bytes):
    if isinstance(str_or_bytes, bytes):
        try:
            return str_or_bytes.decode()
        except UnicodeDecodeError:
            return ""
    return str_or_bytes


def make_metadata(replay_id: str, replay: ParsedReplayData):
    launched_at = replay.header["launched_at"]
    title = replay.header["title"]
    game_type = ensure_str(replay.header["game_type"])
    map_file = ensure_str(replay.header["map_file"])
    players = []
    for army_id, player in replay.header["armies"].items():
        if not player["Human"]:
            continue
        nickname = ensure_str(player["PlayerName"])
        clan = player.get("PlayerClan")
        players.append(ReplayPlayerMetadata(
            nickname=nickname,
            player_id=ensure_str(player["OwnerID"]),
            country=ensure_str(player.get("Country")),
            faction=int(player["Faction"]),
            rating_mean=player["MEAN"],
            rating_std=player["DEV"],
            clan=ensure_str(clan if clan else ""),
            team=int(player["Team"]),
            rating=replay.header["scenario"]["Options"]["Ratings"][nickname],
        ))
    return ReplayMetadata(
        title=title,
        replay_id=replay_id,
        launched_at_ts=launched_at,
        duration=replay.duration,
        map=map_file,
        players=players,
        type=game_type
    )


def extract_data(replay_id: str):
    logging.info(f"Extracting data from replay {replay_id}")

    if has_metadata(replay_id, METADATA_VERSION):
        logging.info(f"\talready parsed replay {replay_id}")
        return get_metadata(replay_id, METADATA_VERSION)

    data = get_replay(replay_id)
    if data is None or len(data) == 0:
        logging.info(f"\tcould not parse data from replay {replay_id}; skipping")
        return None

    data = io.BytesIO(data)
    try:
        parsed_replay = parse_replay(data)
    except JSONDecodeError:
        logging.info("\tinvalid replay file!")
        return None
    except AttributeError:
        logging.info("\tinvalid replay data!")
        return None
    metadata = make_metadata(replay_id, parsed_replay)
    write_metadata(replay_id, metadata, METADATA_VERSION)
    logging.info(f"\tdone!")
    return metadata


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    for replay_id in list_replays():
        extract_data(replay_id)
