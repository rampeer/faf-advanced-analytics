import datetime
from enum import IntEnum
from typing import TypeVar, Any, Optional
from uuid import uuid4

import sqlalchemy
from sqlalchemy import JSON, TIMESTAMP, create_engine, func, BLOB, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, Session, relationship

_engine = None


class Timestamp(int):
    ...


class Factions(IntEnum):
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
