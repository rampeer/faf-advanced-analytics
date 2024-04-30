from __future__ import annotations

import io
from json import JSONDecodeError
from typing import Optional, List

from sqlalchemy.orm import sessionmaker

from src.replay_db import get_engine, ReplayDownload, PlayerReplay, Factions, Replay
from src.faf_replay import read_replay
import logging


def ensure_str(str_or_bytes: str | bytes):
    if isinstance(str_or_bytes, bytes):
        return str_or_bytes.decode("utf-8")
    return str_or_bytes


def extract_data():
    engine = get_engine()
    session = sessionmaker(engine)()
    replays = (
        session
        .query(ReplayDownload)
    )
    for r in replays:
        logging.info(f"Processing {r.replay_id}...")
        replay_data = session.query(Replay).filter(Replay.replay_id == r.replay_id).one_or_none()
        if replay_data is not None:
            logging.info(f"Found replay data {replay_data} with {len(replay_data.players)} players; skipping")
            continue
        if r.data is None or len(r.data) == 0:
            logging.info(f"Could not parse data from replay {r.replay_id}; skipping")
            continue
        data = io.BytesIO(r.data)
        try:
            header, _messages = read_replay(data)
            players = []
            for army_id, player in header["armies"].items():
                if not player["Human"]:
                    continue
                nickname = ensure_str(player["PlayerName"])
                clan = player.get("PlayerClan")
                players.append(PlayerReplay(
                    replay_id=r.replay_id,
                    nickname=nickname,
                    account_id=ensure_str(player["OwnerID"]),
                    country=ensure_str(player.get("Country")),
                    faction=int(player["Faction"]),
                    rating_mean=player["MEAN"],
                    rating_stddev=player["DEV"],
                    clan=ensure_str(clan if clan else None),
                    team=int(player["Team"]),
                    rating=header["scenario"]["Options"]["Ratings"][nickname]
                ))
            session.add(Replay(replay_id=r.replay_id))
            session.add_all(players)
            session.commit()
            logging.info(f"Extracted {len(players)} players from {r.replay_id}")
        except JSONDecodeError:
            print(f"Cannot parse replay {r.replay_id}")


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    extract_data()
