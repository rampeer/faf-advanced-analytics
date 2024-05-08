from __future__ import annotations

import io
import traceback
from json import JSONDecodeError
import logging

from src.faf_replay import parse_replay
from src.storage import has_metadata, get_metadata, write_metadata, list_replays, get_replay

METADATA_VERSION = 1


def extract_data(replay_id: str):
    logging.info(f"Extracting data from replay {replay_id}")

    if has_metadata(replay_id, METADATA_VERSION):
        logging.info(f"\talready parsed replay {replay_id}")
        return get_metadata(replay_id, METADATA_VERSION)

    try:
        data = get_replay(replay_id)
        if data is None or len(data) == 0:
            logging.info(f"\tcould not parse data from replay {replay_id}; skipping")
            return None
        data = io.BytesIO(data)
        metadata = parse_replay(data, replay_id)
        write_metadata(replay_id, metadata, METADATA_VERSION)
    except JSONDecodeError:
        logging.warning("\tProvided file is not a valid replay file!")
        return None
    except AttributeError:
        logging.warning("\tInvalid replay data!")
        logging.warning(traceback.format_exc())
        return None
    except Exception:
        logging.error("\tSomething went wrong, unexpectedly!")
        logging.error(traceback.format_exc())
        return None
    logging.info(f"\tdone!")
    return metadata


if __name__ == '__main__':
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    for replay_id in list_replays():
        extract_data(replay_id)
