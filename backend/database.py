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


def get_sensor_value_by_feed_key(sensor_feed_key: str) -> Optional[Any]:
    with Session(_require_engine()) as session:
        sensor_columns = _get_table_columns(session, "sensors")
        if not sensor_columns:
            return None

        value_col = "current_value" if "current_value" in sensor_columns else (
            "value" if "value" in sensor_columns else None
        )
        if not value_col:
            return None

        row = session.execute(
            text(f"SELECT {value_col} FROM sensors WHERE feed_key = :feed_key LIMIT 1"),
            {"feed_key": sensor_feed_key},
        ).first()
        if not row:
            return None
        return row[0]


def list_sensors_from_db() -> list[dict[str, Any]]:
    with Session(_require_engine()) as session:
        sensor_columns = _get_table_columns(session, "sensors")
        if not sensor_columns:
            return []

        value_col = "current_value" if "current_value" in sensor_columns else (
            "value" if "value" in sensor_columns else None
        )
        time_col = "last_recorded_at" if "last_recorded_at" in sensor_columns else (
            "last_record_time" if "last_record_time" in sensor_columns else None
        )

        select_cols = ["feed_key", "name", "type"]
        if value_col:
            select_cols.append(f"{value_col} AS current_value")
        else:
            select_cols.append("NULL AS current_value")
        if time_col:
            select_cols.append(f"{time_col} AS last_recorded_at")
        else:
            select_cols.append("NULL AS last_recorded_at")

        query = f"SELECT {', '.join(select_cols)} FROM sensors ORDER BY id ASC"
        rows = session.execute(text(query)).mappings().all()
        return [dict(row) for row in rows]


def list_devices_from_db() -> list[dict[str, Any]]:
    with Session(_require_engine()) as session:
        device_columns = _get_table_columns(session, "devices")
        if not device_columns:
            return []

        value_col = "value" if "value" in device_columns else (
            "current_value" if "current_value" in device_columns else None
        )
        time_col = "last_record_time" if "last_record_time" in device_columns else (
            "last_recorded_at" if "last_recorded_at" in device_columns else None
        )

        select_cols = ["feed_key", "name", "type", "status"]
        if value_col:
            select_cols.append(f"{value_col} AS value")
        else:
            select_cols.append("NULL AS value")
        if time_col:
            select_cols.append(f"{time_col} AS last_record_time")
        else:
            select_cols.append("NULL AS last_record_time")

        query = f"SELECT {', '.join(select_cols)} FROM devices ORDER BY id ASC"
        rows = session.execute(text(query)).mappings().all()
        return [dict(row) for row in rows]


def get_device_value_by_feed_key(device_feed_key: str) -> Optional[Any]:
    with Session(_require_engine()) as session:
        device_columns = _get_table_columns(session, "devices")
        if not device_columns:
            return None

        value_col = "value" if "value" in device_columns else (
            "current_value" if "current_value" in device_columns else None
        )
        if not value_col:
            return None

        row = session.execute(
            text(f"SELECT {value_col} FROM devices WHERE feed_key = :feed_key LIMIT 1"),
            {"feed_key": device_feed_key},
        ).first()
        if not row:
            return None
        return row[0]


def _parse_adafruit_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Adafruit timestamps are ISO-8601 and often end with "Z".
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _get_table_columns(session: Session, table_name: str) -> set[str]:
    rows = session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).all()
    return {row[0] for row in rows}


def sync_feed_latest_values(feeds: list[dict[str, Any]]) -> None:
    """
    Persist latest Adafruit feed values into both devices/sensors tables by feed_key.
    Non-matching feed keys are ignored by UPDATE statements.
    """
    if not feeds:
        return

    with Session(_require_engine()) as session:
        device_columns = _get_table_columns(session, "devices")
        sensor_columns = _get_table_columns(session, "sensors")

        device_value_col = "value" if "value" in device_columns else (
            "current_value" if "current_value" in device_columns else None
        )
        device_time_col = "last_record_time" if "last_record_time" in device_columns else (
            "last_recorded_at" if "last_recorded_at" in device_columns else None
        )

        sensor_value_col = "current_value" if "current_value" in sensor_columns else (
            "value" if "value" in sensor_columns else None
        )
        sensor_time_col = "last_recorded_at" if "last_recorded_at" in sensor_columns else (
            "last_record_time" if "last_record_time" in sensor_columns else None
        )

        for feed in feeds:
            feed_key = feed.get("key")
            if not feed_key:
                continue

            last_data = feed.get("last_data") or {}
            latest_value = last_data.get("value")
            if latest_value is None:
                latest_value = feed.get("last_value")
            if latest_value is None:
                continue

            recorded_at = _parse_adafruit_time(last_data.get("created_at"))

            if device_value_col:
                if device_time_col:
                    session.execute(
                        text(
                            f"""
                            UPDATE devices
                            SET
                                {device_value_col} = :value,
                                {device_time_col} = COALESCE(:recorded_at, {device_time_col})
                            WHERE feed_key = :feed_key
                            """
                        ),
                        {
                            "feed_key": feed_key,
                            "value": str(latest_value),
                            "recorded_at": recorded_at,
                        },
                    )
                else:
                    session.execute(
                        text(
                            f"""
                            UPDATE devices
                            SET {device_value_col} = :value
                            WHERE feed_key = :feed_key
                            """
                        ),
                        {
                            "feed_key": feed_key,
                            "value": str(latest_value),
                        },
                    )

            if sensor_value_col:
                if sensor_time_col:
                    session.execute(
                        text(
                            f"""
                            UPDATE sensors
                            SET
                                {sensor_value_col} = :value,
                                {sensor_time_col} = COALESCE(:recorded_at, {sensor_time_col})
                            WHERE feed_key = :feed_key
                            """
                        ),
                        {
                            "feed_key": feed_key,
                            "value": str(latest_value),
                            "recorded_at": recorded_at,
                        },
                    )
                else:
                    session.execute(
                        text(
                            f"""
                            UPDATE sensors
                            SET {sensor_value_col} = :value
                            WHERE feed_key = :feed_key
                            """
                        ),
                        {
                            "feed_key": feed_key,
                            "value": str(latest_value),
                        },
                    )

        session.commit()
