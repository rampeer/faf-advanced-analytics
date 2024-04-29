import logging
from typing import Optional

import requests
from sqlalchemy.orm import sessionmaker

from faf_replay_scrape.src.replay_db import get_engine, ReplayDownload

REPLAY_URL_BASE = "https://replay.faforever.com/"


def load_replay(url: str):
    response = requests.get(url)
    return response.content


def download_replays(from_id: int, to_id: int, refresh: bool = False):
    engine = get_engine()
    session = sessionmaker(engine)()
    for replay_id in range(from_id, to_id + 1):
        logging.info(f"Checking replay {replay_id}...")
        replay: Optional[ReplayDownload] = (
            session
            .query(ReplayDownload)
            .filter(ReplayDownload.replay_id == replay_id)
            .first()
        )
        if refresh and replay:
            logging.info(f"Refreshing replay {replay_id}")
            session.delete(replay)
            session.commit()
        if replay is None:
            url = REPLAY_URL_BASE + str(replay_id)
            data = load_replay(url)
            replay = ReplayDownload(replay_id=str(replay_id), data=data)
            session.add(replay)
            session.commit()
            logging.info(f"Done!")
        else:
            logging.info(f"Skipping")


if __name__ == '__main__':
    download_replays(21708980, 21709000)
