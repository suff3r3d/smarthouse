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
        "value": schedule.value,
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
    value: str,
    trigger_time: datetime,
):
    with Session(_require_engine()) as session:
        existing = session.execute(
            select(Schedule).where(
                Schedule.setting_profile_id == setting_profile_id,
                Schedule.device_id == device_id,
            )
        ).scalars().first()

        if existing:
            existing.value = value
            existing.trigger_time = trigger_time
            session.commit()
            session.refresh(existing)
            return existing

        schedule = Schedule(
            setting_profile_id=setting_profile_id,
            device_id=device_id,
            value=value,
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
    value: Optional[str] = None,
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
        if value is not None:
            schedule.value = value
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


def get_current_setting_profile_id_by_user_id(user_id: int) -> Optional[int]:
    with Session(_require_engine()) as session:
        row = session.execute(
            text(
                """
                SELECT current_setting_profile_id
                FROM users
                WHERE id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        ).first()
        if not row:
            return None
        return row[0]


def get_setting_profile_thresholds(setting_profile_id: int) -> Optional[dict[str, Any]]:
    with Session(_require_engine()) as session:
        row = session.execute(
            text(
                """
                SELECT
                    id AS setting_profile_id,
                    temp_lower_threshold,
                    temp_upper_threshold,
                    humidity_lower_threshold,
                    humidity_upper_threshold,
                    gas_upper_threshold,
                    light_lower_threshold
                FROM setting_profiles
                WHERE id = :setting_profile_id
                LIMIT 1
                """
            ),
            {"setting_profile_id": setting_profile_id},
        ).mappings().first()
        return dict(row) if row else None


def update_setting_profile_thresholds(
    *,
    setting_profile_id: int,
    temp_lower_threshold: Optional[float] = None,
    temp_upper_threshold: Optional[float] = None,
    humidity_lower_threshold: Optional[float] = None,
    humidity_upper_threshold: Optional[float] = None,
    gas_upper_threshold: Optional[float] = None,
    light_lower_threshold: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    with Session(_require_engine()) as session:
        updates: dict[str, Any] = {}
        if temp_lower_threshold is not None:
            updates["temp_lower_threshold"] = temp_lower_threshold
        if temp_upper_threshold is not None:
            updates["temp_upper_threshold"] = temp_upper_threshold
        if humidity_lower_threshold is not None:
            updates["humidity_lower_threshold"] = humidity_lower_threshold
        if humidity_upper_threshold is not None:
            updates["humidity_upper_threshold"] = humidity_upper_threshold
        if gas_upper_threshold is not None:
            updates["gas_upper_threshold"] = gas_upper_threshold
        if light_lower_threshold is not None:
            updates["light_lower_threshold"] = light_lower_threshold

        if updates:
            set_clause = ", ".join([f"{col} = :{col}" for col in updates.keys()])
            params = {"setting_profile_id": setting_profile_id, **updates}
            session.execute(
                text(
                    f"""
                    UPDATE setting_profiles
                    SET {set_clause}
                    WHERE id = :setting_profile_id
                    """
                ),
                params,
            )
            session.commit()

        row = session.execute(
            text(
                """
                SELECT
                    id AS setting_profile_id,
                    temp_lower_threshold,
                    temp_upper_threshold,
                    humidity_lower_threshold,
                    humidity_upper_threshold,
                    gas_upper_threshold,
                    light_lower_threshold
                FROM setting_profiles
                WHERE id = :setting_profile_id
                LIMIT 1
                """
            ),
            {"setting_profile_id": setting_profile_id},
        ).mappings().first()
        return dict(row) if row else None


def get_admin_alert_thresholds() -> dict[str, float | None]:
    """
    Return alert thresholds from the house owner's setting profile.
    Assumes single-owner/single-profile deployment but degrades safely.
    """
    default_temp = 35.0
    default_temp_lower = 15.0
    default_humidity_lower = 30.0
    default_humidity_upper = 70.0
    default_gas = 800.0
    default_light_lower = 20.0

    with Session(_require_engine()) as session:
        profile_columns = _get_table_columns(session, "setting_profiles")
        has_temp_lower = "temp_lower_threshold" in profile_columns
        has_temp_upper = "temp_upper_threshold" in profile_columns
        has_humidity_lower = "humidity_lower_threshold" in profile_columns
        has_humidity_upper = "humidity_upper_threshold" in profile_columns
        has_gas_upper = "gas_upper_threshold" in profile_columns
        has_light_lower = "light_lower_threshold" in profile_columns

        temp_lower_expr = "sp.temp_lower_threshold AS temp_lower_threshold" if has_temp_lower else "NULL AS temp_lower_threshold"
        temp_expr = "sp.temp_upper_threshold AS temp_upper_threshold" if has_temp_upper else "NULL AS temp_upper_threshold"
        humidity_lower_expr = "sp.humidity_lower_threshold AS humidity_lower_threshold" if has_humidity_lower else "NULL AS humidity_lower_threshold"
        humidity_upper_expr = "sp.humidity_upper_threshold AS humidity_upper_threshold" if has_humidity_upper else "NULL AS humidity_upper_threshold"
        gas_expr = "sp.gas_upper_threshold AS gas_upper_threshold" if has_gas_upper else "NULL AS gas_upper_threshold"
        light_lower_expr = "sp.light_lower_threshold AS light_lower_threshold" if has_light_lower else "NULL AS light_lower_threshold"

        row = session.execute(
            text(
                f"""
                SELECT
                    {temp_lower_expr},
                    {temp_expr},
                    {humidity_lower_expr},
                    {humidity_upper_expr},
                    {gas_expr},
                    {light_lower_expr}
                FROM users u
                JOIN setting_profiles sp
                  ON sp.user_id = u.id
                WHERE u.is_house_owner = TRUE
                ORDER BY
                    CASE WHEN u.current_setting_profile_id = sp.id THEN 0 ELSE 1 END,
                    sp.id ASC
                LIMIT 1
                """
            )
        ).mappings().first()

        temp_lower_threshold = default_temp_lower
        temp_threshold = default_temp
        humidity_lower_threshold = default_humidity_lower
        humidity_upper_threshold = default_humidity_upper
        gas_threshold = default_gas
        light_lower_threshold = default_light_lower

        if row:
            try:
                if row.get("temp_lower_threshold") is not None:
                    temp_lower_threshold = float(row.get("temp_lower_threshold"))
            except (TypeError, ValueError):
                pass

            try:
                if row.get("temp_upper_threshold") is not None:
                    temp_threshold = float(row.get("temp_upper_threshold"))
            except (TypeError, ValueError):
                pass

            try:
                if row.get("gas_upper_threshold") is not None:
                    gas_threshold = float(row.get("gas_upper_threshold"))
            except (TypeError, ValueError):
                pass

            try:
                if row.get("humidity_lower_threshold") is not None:
                    humidity_lower_threshold = float(row.get("humidity_lower_threshold"))
            except (TypeError, ValueError):
                pass

            try:
                if row.get("humidity_upper_threshold") is not None:
                    humidity_upper_threshold = float(row.get("humidity_upper_threshold"))
            except (TypeError, ValueError):
                pass

            try:
                if row.get("light_lower_threshold") is not None:
                    light_lower_threshold = float(row.get("light_lower_threshold"))
            except (TypeError, ValueError):
                pass

        return {
            "temp_lower_threshold": temp_lower_threshold,
            "temp_upper_threshold": temp_threshold,
            "humidity_lower_threshold": humidity_lower_threshold,
            "humidity_upper_threshold": humidity_upper_threshold,
            "gas_upper_threshold": gas_threshold,
            "light_lower_threshold": light_lower_threshold,
        }


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


def get_sensor_timeseries(
    *,
    feed_key: str,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    with Session(_require_engine()) as session:
        rows = session.execute(
            text(
                """
                SELECT timestamp, value
                FROM sensor_data
                WHERE feed_key = :feed_key
                  AND timestamp >= :start_time
                  AND timestamp <= :end_time
                ORDER BY timestamp ASC
                """
            ),
            {
                "feed_key": feed_key,
                "start_time": start_time,
                "end_time": end_time,
            },
        ).mappings().all()
        return [dict(row) for row in rows]


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

        unit_col = "unit" if "unit" in sensor_columns else None

        select_cols = ["feed_key", "name", "type"]
        if unit_col:
            select_cols.append(f"{unit_col} AS unit")
        else:
            select_cols.append("NULL AS unit")
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


def list_alerts(limit: int = 100, since: Optional[datetime] = None) -> list[dict[str, Any]]:
    with Session(_require_engine()) as session:
        alert_columns = _get_table_columns(session, "alerts")
        has_alert_type = "alert_type" in alert_columns
        has_feed_key = "feed_key" in alert_columns

        select_alert_type = "a.alert_type AS alert_type" if has_alert_type else "'WARNING' AS alert_type"
        select_feed_key = "a.feed_key AS feed_key" if has_feed_key else "NULL AS feed_key"
        where_clause = "WHERE a.created_at > :since" if since is not None else ""
        params = {"limit": limit}
        if since is not None:
            params["since"] = since
        rows = session.execute(
            text(
                f"""
                SELECT
                    {select_alert_type},
                    {select_feed_key},
                    a.message,
                    a.created_at
                FROM alerts a
                {where_clause}
                ORDER BY a.created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()

        result = []
        for row in rows:
            feed_key = row.get("feed_key")
            title = f"Alert from {feed_key}" if feed_key else "System Alert"
            result.append(
                {
                    "type": row.get("alert_type") or "WARNING",
                    "title": title,
                    "msg": row.get("message"),
                    "timestamp": row.get("created_at"),
                    "feed_key": feed_key,
                }
            )
        return result


def create_alert(
    *,
    alert_type: str,
    message: str,
    feed_key: Optional[str] = None,
) -> None:
    with Session(_require_engine()) as session:
        alert_columns = _get_table_columns(session, "alerts")
        has_alert_type = "alert_type" in alert_columns
        has_feed_key = "feed_key" in alert_columns

        if feed_key:
            if has_feed_key and has_alert_type:
                session.execute(
                    text(
                        """
                        INSERT INTO alerts (alert_type, feed_key, message)
                        VALUES (:alert_type, :feed_key, :message)
                        """
                    ),
                    {
                        "alert_type": alert_type,
                        "feed_key": feed_key,
                        "message": message,
                    },
                )
            elif has_feed_key:
                session.execute(
                    text(
                        """
                        INSERT INTO alerts (feed_key, message)
                        VALUES (:feed_key, :message)
                        """
                    ),
                    {
                        "feed_key": feed_key,
                        "message": message,
                    },
                )
            else:
                raise Exception("alerts.feed_key column is required")
        else:
            if has_feed_key and has_alert_type:
                session.execute(
                    text(
                        """
                        INSERT INTO alerts (alert_type, feed_key, message)
                        VALUES (:alert_type, NULL, :message)
                        """
                    ),
                    {
                        "alert_type": alert_type,
                        "message": message,
                    },
                )
            elif has_feed_key:
                session.execute(
                    text(
                        """
                        INSERT INTO alerts (feed_key, message)
                        VALUES (NULL, :message)
                        """
                    ),
                    {
                            "message": message,
                    },
                )
            else:
                raise Exception("alerts.feed_key column is required")

        session.commit()


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
        sensor_data_columns = _get_table_columns(session, "sensor_data")
        has_sensor_data_table = bool(sensor_data_columns)

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

                if has_sensor_data_table:
                    session.execute(
                        text(
                            """
                            INSERT INTO sensor_data (timestamp, feed_key, value)
                            VALUES (NOW(), :feed_key, :value)
                            """
                        ),
                        {
                            "feed_key": feed_key,
                            "value": str(latest_value),
                        },
                    )

        session.commit()
