from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

action_type_enum = ENUM(
    "TURN_ON",
    "TURN_OFF",
    "SET_VALUE",
    name="action_type",
    create_type=False,
)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    password_hash: Mapped[str]
    is_house_owner: Mapped[bool]

    def __repr__(self):
        return f"User({self.username})"


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    setting_profile_id: Mapped[int] = mapped_column(
        ForeignKey("setting_profiles.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(action_type_enum, nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    trigger_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
