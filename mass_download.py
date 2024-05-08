import logging
from typing import Optional

import requests
from sqlalchemy.orm import sessionmaker
import argparse

from src.replay_db import get_engine, ReplayDownload
from src.storage import list_replays, write_replay, has_replay, ensure_dirs

REPLAY_URL_BASE = "https://replay.faforever.com/"


def _load_replay(url: str):
    try:
        response = requests.get(url)
    except requests.exceptions.SSLError:
        logging.warning("SSL error occurred")
        return None
    if response.status_code == 200:
        return response.content
    logging.info(f"\tReceived response {response.status_code}")
    return None


def download_replays(from_id: int, to_id: int, refresh: bool = False):
    ensure_dirs()
    for replay_id in range(from_id, to_id + 1):
        logging.info(f"Checking replay {replay_id}...")
        if has_replay(str(replay_id)):
            if refresh:
                logging.info(f"\trefreshing replay {replay_id}")
            else:
                logging.info(f"\talready downloaded replay {replay_id}")
                continue
        url = REPLAY_URL_BASE + str(replay_id)
        data = _load_replay(url)
        if data:
            write_replay(str(replay_id), data)
            logging.info(f"\tdone!")
        else:
            write_replay(str(replay_id), b'')
            logging.info(f"\treplay not found!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download replays from Faforever")
    parser.add_argument("--from_id", type=int, help="Starting Replay ID", default=21_700_000)
    parser.add_argument("--to_id", type=int, help="Ending Replay ID (inclusive)", default=21_708_086)
    parser.add_argument("--refresh", action="store_true", help="Refresh existing replays?", default=False)
    args = parser.parse_args()
    logging.basicConfig(encoding='utf-8', level=logging.INFO)
    download_replays(args.from_id, args.to_id)
