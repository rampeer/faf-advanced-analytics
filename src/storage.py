import os.path
from glob import glob
from os.path import basename
import shelve

METADATA_FILE = "metadata.shelve"
METADATA_VERSION_SUFFIX = "_version"
REPLAY_DIR = "data/replays/"
CHAT_DIR = "data/chats/"
FAF_REPLAY_EXTENSION = ".fafreplay"

metadata = shelve.open(METADATA_FILE)


def ensure_dirs():
    if not os.path.exists(REPLAY_DIR):
        os.makedirs(REPLAY_DIR)
    if not os.path.exists(CHAT_DIR):
        os.makedirs(CHAT_DIR)


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


def write_metadata(replay_id, obj, version):
    metadata[replay_id] = obj
    metadata[replay_id + METADATA_VERSION_SUFFIX] = version


def has_metadata(replay_id, version):
    return metadata.get(replay_id + METADATA_VERSION_SUFFIX) == version


def get_metadata(replay_id, version):
    if not has_metadata(replay_id, version):
        return None
    return metadata[replay_id]
