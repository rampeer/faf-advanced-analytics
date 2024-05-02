import os.path
from glob import glob
from os.path import basename

REPLAY_DIR = "data/replays/"
FAF_REPLAY_EXTENSION = ".fafreplay"


def ensure_replay_dir():
    if not os.path.exists(REPLAY_DIR):
        os.makedirs(REPLAY_DIR)


def list_replays():
    replay_files = [basename(_)[:-len(FAF_REPLAY_EXTENSION)] for _ in glob(REPLAY_DIR + "*" + FAF_REPLAY_EXTENSION)]
    return replay_files


def has_replay(replay_id):
    return os.path.exists(REPLAY_DIR + replay_id + FAF_REPLAY_EXTENSION)


def get_replay(replay_id):
    with open(REPLAY_DIR + replay_id + FAF_REPLAY_EXTENSION, "rb") as f:
        return f.read()


def write_replay(replay_id, data):
    with open(REPLAY_DIR + replay_id + FAF_REPLAY_EXTENSION, "wb") as f:
        return f.write(data)
