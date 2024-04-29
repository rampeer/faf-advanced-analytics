import io
from json import JSONDecodeError
from typing import Optional, List

from sqlalchemy.orm import sessionmaker

from faf_replay_scrape.src.replay_db import get_engine, ReplayDownload
from src.faf_replay import read_replay


def extract_data():
    engine = get_engine()
    session = sessionmaker(engine)()
    replay = (
        session
        .query(ReplayDownload)
    )
    for r in replay:
        if r.data is None or len(r.data) == 0:
            continue
        data = io.BytesIO(r.data)
        try:
            header, _messages = read_replay(data)
        except JSONDecodeError:
            print(f"Cannot parse replay {r.replay_id}")
        print(header)


if __name__ == '__main__':
    extract_data()
