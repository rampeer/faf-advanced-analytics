from __future__ import annotations

import io
from dataclasses import dataclass
from json import JSONDecodeError
import logging

from src.faf_replay import parse_replay, ParsedReplayData
from src.storage import has_metadata, get_metadata, write_metadata, list_replays, get_replay

METADATA_VERSION = 1


def ensure_str(str_or_bytes: str | bytes):
    if isinstance(str_or_bytes, bytes):
        try:
            return str_or_bytes.decode()
        except UnicodeDecodeError:
            return ""
    return str_or_bytes


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
