import datetime
from enum import Enum
from typing import TypeVar, Any, Optional
from uuid import uuid4

import sqlalchemy
from sqlalchemy import JSON, TIMESTAMP, create_engine, func, BLOB, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session, relationship

_engine = None


class Timestamp(int):
    ...


class Factions(Enum):
    UEF = 1
    Cybran = 2
    Aeon = 3
    Seraphim = 4


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


class Account(Base):
    __tablename__ = "account"
    account_id: Mapped[str] = mapped_column(primary_key=True)
    player_replays = relationship("PlayerReplay", back_populates="account")


class Replay(Base):
    __tablename__ = "replay"
    replay_id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[Timestamp] = mapped_column(default=lambda: datetime.datetime.now())
    players = relationship("PlayerReplay", back_populates="replay")


class PlayerReplay(Base):
    __tablename__ = "player_replay"
    replay_id: Mapped[str] = mapped_column(ForeignKey('replay.replay_id'), primary_key=True)
    replay = relationship("Replay")

    account_id: Mapped[str] = mapped_column(ForeignKey('account.account_id'), primary_key=True)
    account = relationship("Account")

    nickname: Mapped[str] = mapped_column()

    country: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    clan: Mapped[str] = mapped_column(default=None, nullable=True)

    rating_mean: Mapped[float]
    rating_stddev: Mapped[float]
    rating: Mapped[float]

    team: Mapped[int]
    faction: Mapped[int]


class ReplayDownload(Base):
    __tablename__ = "replay_download"
    replay_id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[Timestamp] = mapped_column(default=lambda: datetime.datetime.now())
    data: Mapped[bytes]


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine("sqlite:///replays.sqlite3", echo=False)
        Base.metadata.create_all(_engine)
    return _engine
