import datetime
from enum import Enum
from typing import TypeVar, Any
from uuid import uuid4

import sqlalchemy
from sqlalchemy import JSON, TIMESTAMP, create_engine, func, BLOB, Integer
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session

_engine = None


class Timestamp(int):
    ...


class Factions(Enum):
    UEF = 0
    Cybran = 1
    Aeon = 2
    Seraphim = 3


class Base(DeclarativeBase):
    type_annotation_map = {
        list[int]: JSON,
        dict[str, Any]: JSON,
        Timestamp: TIMESTAMP,
        Factions: Integer
    }

    def as_dict(self, related_fields=None):
        if related_fields is None:
            related_fields = []

        serialized = {}

        for column in self.__table__.columns:
            serialized[column.name] = getattr(self, column.name)

        for field in related_fields:
            related = getattr(self, field)
            serialized[field] = related.as_dict() if related else None

        return serialized


class ReplayDownload(Base):
    __tablename__ = "entries"
    replay_id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[Timestamp] = mapped_column(default=lambda: datetime.datetime.now())
    data: Mapped[bytes]


class Players(Base):
    __tablename__ = "players"
    nickname: Mapped[str] = mapped_column(primary_key=True)


class PlayerInReplay(Base):
    __tablename__ = "player_in_replay"
    replay: Mapped[str] = mapped_column(primary_key=True)

    nickname: Mapped[str] = mapped_column(primary_key=True)
    country: Mapped[str]

    rating_mean: Mapped[float]
    rating_stddev: Mapped[float]
    rating: Mapped[float]

    team: Mapped[int]
    faction: Mapped[Factions]


class ReplayMetadata(Base):
    __tablename__ = "replay_metadata"
    replay_id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[Timestamp] = mapped_column(default=lambda: datetime.datetime.now())
    data: Mapped[bytes]


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine("sqlite:///replays.sqlite3", echo=False)
        Base.metadata.create_all(_engine)
    return _engine
