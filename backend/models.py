from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    password_hash: Mapped[str]
    is_house_owner: Mapped[bool]
    house_owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

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
    value: Mapped[str] = mapped_column(nullable=False)
    trigger_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
