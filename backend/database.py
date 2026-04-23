import os
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Any, Optional

from models import Schedule, User

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/smarthouse")

engine = None


def _require_engine():
    if not engine:
        raise Exception("Engine not initialized. Call connect() first.")
    return engine

async def connect():
  global engine
  engine = create_engine(
      DATABASE_URL, 
      echo=True, 
      connect_args={"options": "-c statement_timeout=5000"}
  )

async def disconnect():
  pass # In a real app, you might want to dispose the engine

def get_user_by_id(user_id: int):
  with Session(_require_engine()) as session:
    stmt = select(User).where(User.id == user_id)
    user = session.execute(stmt).scalars().first()
    return user

def get_user_by_username(username: str):
  with Session(_require_engine()) as session:
    stmt = select(User).where(User.username == username)
    user = session.execute(stmt).scalars().first()
    return user

def create_user(user: User):
    with Session(_require_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def schedule_to_dict(schedule: Schedule) -> dict[str, Any]:
    return {
        "id": schedule.id,
        "setting_profile_id": schedule.setting_profile_id,
        "device_id": schedule.device_id,
        "action": schedule.action,
        "payload": schedule.payload,
        "trigger_time": schedule.trigger_time,
    }


def list_schedules(setting_profile_id: Optional[int] = None, device_id: Optional[int] = None):
    with Session(_require_engine()) as session:
        stmt = select(Schedule).order_by(Schedule.trigger_time.asc())
        if setting_profile_id is not None:
            stmt = stmt.where(Schedule.setting_profile_id == setting_profile_id)
        if device_id is not None:
            stmt = stmt.where(Schedule.device_id == device_id)
        return session.execute(stmt).scalars().all()


def list_schedules_by_profile_ids(profile_ids: list[int], device_id: Optional[int] = None):
    if not profile_ids:
        return []
    with Session(_require_engine()) as session:
        stmt = select(Schedule).where(Schedule.setting_profile_id.in_(profile_ids))
        stmt = stmt.order_by(Schedule.trigger_time.asc())
        if device_id is not None:
            stmt = stmt.where(Schedule.device_id == device_id)
        return session.execute(stmt).scalars().all()


def get_schedule_by_id(schedule_id: int):
    with Session(_require_engine()) as session:
        stmt = select(Schedule).where(Schedule.id == schedule_id)
        return session.execute(stmt).scalars().first()


def create_schedule(
    setting_profile_id: int,
    device_id: int,
    action: str,
    trigger_time: datetime,
    payload: Optional[dict[str, Any]] = None,
):
    with Session(_require_engine()) as session:
        schedule = Schedule(
            setting_profile_id=setting_profile_id,
            device_id=device_id,
            action=action,
            payload=payload,
            trigger_time=trigger_time,
        )
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        return schedule


def update_schedule(
    schedule_id: int,
    *,
    setting_profile_id: Optional[int] = None,
    device_id: Optional[int] = None,
    action: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    trigger_time: Optional[datetime] = None,
):
    with Session(_require_engine()) as session:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            return None

        if setting_profile_id is not None:
            schedule.setting_profile_id = setting_profile_id
        if device_id is not None:
            schedule.device_id = device_id
        if action is not None:
            schedule.action = action
        if payload is not None:
            schedule.payload = payload
        if trigger_time is not None:
            schedule.trigger_time = trigger_time

        session.commit()
        session.refresh(schedule)
        return schedule


def delete_schedule(schedule_id: int) -> bool:
    with Session(_require_engine()) as session:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            return False
        session.delete(schedule)
        session.commit()
        return True


def get_setting_profile_ids_by_user_id(user_id: int) -> list[int]:
    with Session(_require_engine()) as session:
        rows = session.execute(
            text("SELECT id FROM setting_profiles WHERE user_id = :user_id ORDER BY id ASC"),
            {"user_id": user_id},
        ).all()
        return [row[0] for row in rows]
