# Smart House Backend API

FastAPI backend for smart-home device control, sensor monitoring, schedules, and alert logging.

## Tech Stack
- FastAPI + Uvicorn
- SQLAlchemy (sync `Session`)
- PostgreSQL
- JWT auth
- Adafruit IO REST API

## Runtime Notes
- Background `device_polling_worker` runs every 60 seconds.
- It fetches Adafruit feeds, updates `devices`/`sensors`, logs sensor time-series into `sensor_data`, and generates alerts.

## Authentication
Use JWT from `POST /api/auth/login`.

Accepted auth token locations:
- `Authorization: Bearer <token>`
- `auth-token: <token>`
- JSON body field `auth_token` (for endpoints that read body)

## Response Format
All JSON responses are wrapped globally:
- Success: `{ "success": true, "data": ... }`
- Error: `{ "success": false, "message": "..." }`

---

## API Reference
Base path: `/api`

### Health / Utility
- `GET /` -> server health
- `GET /get-user-by-username?username=...`
- `GET /api/hello`

### Authentication
- `POST /api/auth/login`
  - Body: `{ "username": "...", "password": "..." }`
  - Returns JWT token

- `POST /api/auth/register`
  - House-owner only (authenticated request)
  - Body: `{ "username": "...", "password": "..." }`
  - Always creates normal user account (`is_house_owner = false`)

- `PUT /api/auth/change-password`
  - Auth: Required (any authenticated user)
  - Body: `{ "current_password": "...", "new_password": "...", "confirm_new_password": "..." }`
  - Password policy: ≥8 characters, at least one uppercase, lowercase, digit, and special character
  - Errors:
    - `400` current password incorrect
    - `400` new password and confirmation do not match
    - `400` new password does not meet strength requirements

### Users
- `GET /api/users`
  - Auth: Required (homeowner and family members)
  - Returns all household users with their role
  - Response `data`:
    - `users`: array of `{ id, username, role, house_owner_id }` where `role` is `"homeowner"` or `"family_member"`, and `house_owner_id` is the ID of the owning homeowner (null for the homeowner themselves)
    - `count`

- `DELETE /api/users/{user_id}`
  - Auth: Required (homeowner only)
  - Deletes a family member account
  - Errors:
    - `403` not house owner
    - `403` target user is the house owner
    - `404` user not found

### Devices
- `GET /api/devices`
  - Reads current device states from database cache
  - Response object per device includes `location` (nullable)

- `POST /api/devices/{device_id}/set_state`
  - Body: `{ "auth_token": "...", "state": <any> }`
  - Publishes value to Adafruit feed

- `GET /api/devices/{device_id}/get_state`
  - Body model still expects `auth_token` in current code
  - Returns cached device state from database

- `PATCH /api/devices/{device_id}`
  - Auth: Required (homeowner only)
  - `device_id` is the feed key (e.g. `lb1`, `door`)
  - Body (at least one field required):
    ```json
    {
      "name": "Living Room Light",
      "location": "Living Room"
    }
    ```
  - Response `data`: `{ message, device: { id, feed_key, name, location } }`
  - Errors:
    - `400` no fields provided
    - `403` not house owner
    - `404` device not found

- `GET /api/device-data`
  - Auth: Required
  - Query: `feed_key`, `start_time` (ISO datetime), `end_time` (ISO datetime)
  - Accepts only device feed keys (`lb1`, `door`, `pir`, `rgb`, `light-pwm`)
  - Returns time-series activity rows from `sensor_data` ordered by timestamp ascending
  - Response `data`:
    - `feed_key`
    - `data`: array of `{ timestamp, value }`
    - `count`

### Sensors
- `GET /api/sensors`
  - Reads current sensor states from database cache
  - Response object per sensor includes `location` (nullable)

- `GET /api/sensors/{sensor_id}/get_value`
  - Auth required
  - Returns cached current sensor value

- `POST /api/sensors/history`
  - Body:
    ```json
    {
      "auth_token": "...",
      "feed_key": "temperature",
      "start_time": "2026-05-13T00:00:00Z",
      "end_time": "2026-05-13T23:59:59Z"
    }
    ```
  - Returns array of rows between `[start_time, end_time]` (inclusive)
  - Each row:
    - `timestamp`
    - `value`

- `GET /api/sensor-data`
  - Auth: Required
  - Query: `feed_key`, `start_time` (ISO datetime), `end_time` (ISO datetime)
  - Accepts any known feed key (`temperature`, `humidity`, `rain`, `gas`, `themis`, `lb1`, `door`, `pir`, `rgb`, `light-pwm`)
  - Returns time-series rows from `sensor_data` ordered by timestamp ascending
  - Response `data`:
    - `feed_key`
    - `data`: array of `{ timestamp, value }`
    - `count`

- `PATCH /api/sensors/{sensor_id}`
  - Auth: Required (homeowner only)
  - `sensor_id` is the feed key (e.g. `temperature`, `humidity`)
  - Body (at least one field required):
    ```json
    {
      "name": "Living Room Temp",
      "location": "Living Room"
    }
    ```
  - Response `data`: `{ message, sensor: { id, feed_key, name, location } }`
  - Errors:
    - `400` no fields provided
    - `403` not house owner
    - `404` sensor not found

- `GET /api/sensors/latest` (stub)
- `GET /api/sensors/export` (stub)

### Schedules

- `GET /api/schedules`
  - Auth: Required
  - Query (optional): `feed_key` (string)
  - Returns schedules that belong to authenticated user’s setting profiles.
  - Response `data` shape: array of schedule objects
    - `id`
    - `setting_profile_id`
    - `feed_key`
    - `value` (string)
    - `trigger_time` (ISO datetime)

- `POST /api/schedules`
  - Auth: `auth_token` in request body (house-owner only)
  - Body:
    ```json
    {
      "auth_token": "<jwt>",
      "feed_key": "door",
      "value": "OPEN",
      "trigger_time": "2026-05-13T10:30:00Z"
    }
    ```
  - Behavior:
    - creates a new schedule row
    - backend decodes token, finds user, then uses that user’s `current_setting_profile_id`
  - Response `data`: created schedule object
  - Errors:
    - `400` invalid schedule payload
    - `400` current setting profile not found for user
    - `401` invalid auth token
    - `403` only house owner can edit

- `GET /api/schedules/{schedule_id}`
  - Auth: Required
  - Returns one schedule by id if it belongs to authenticated user’s setting profiles.
  - Response `data`: schedule object
  - Errors:
    - `404` schedule not found
    - `403` schedule does not belong to authenticated user

- `PUT /api/schedules/{schedule_id}`
  - Auth: `auth_token` in request body (house-owner only)
  - Body (all fields optional):
    ```json
    {
      "auth_token": "<jwt>",
      "feed_key": "lb1",
      "value": "75",
      "trigger_time": "2026-05-13T11:00:00Z"
    }
    ```
  - Behavior:
    - updates provided fields of the existing schedule
    - keeps existing `setting_profile_id` unchanged
    - enforces profile ownership checks
  - Response `data`: updated schedule object
  - Errors:
    - `401` invalid auth token
    - `403` only house owner can edit
    - `403` schedule/profile does not belong to authenticated user
    - `404` schedule not found

### Setting Profiles

- `POST /api/setting-profiles/current/thresholds`
  - Auth: `auth_token` in request body
  - Body:
    ```json
    {
      "auth_token": "<jwt>"
    }
    ```
  - Returns thresholds of authenticated user's current setting profile.
  - Response `data`:
    - `setting_profile_id`
    - `name`
    - `temp_lower_threshold`
    - `temp_upper_threshold`
    - `humidity_lower_threshold`
    - `humidity_upper_threshold`
    - `gas_upper_threshold`
    - `light_lower_threshold`

- `PUT /api/setting-profiles/current/thresholds`
  - Auth: `auth_token` in request body
  - Body (all threshold fields optional):
    ```json
    {
      "auth_token": "<jwt>",
      "temp_lower_threshold": 15.0,
      "temp_upper_threshold": 35.0,
      "humidity_lower_threshold": 30.0,
      "humidity_upper_threshold": 70.0,
      "gas_upper_threshold": 800.0,
      "light_lower_threshold": 20.0
    }
    ```
  - Behavior:
    - updates only provided fields on current setting profile
    - validates:
      - `temp_lower_threshold < temp_upper_threshold`
      - `humidity_lower_threshold < humidity_upper_threshold`
      - `gas_upper_threshold >= 0`
      - `light_lower_threshold >= 0`
  - Response `data`: full updated thresholds object (includes `name`)

### Modes

- `GET /api/system/mode`
  - Auth: Required
  - Returns all mode flags for the authenticated user's current profile: `name`, `away_mode`, `automation_mode`, `door_auto_lock`, `door_auto_lock_delay_sec`

- `GET /api/modes/away`
  - Auth: Required
  - Returns `{ name, away_mode }`

- `PUT /api/modes/away`
  - Auth: Required (homeowner only)
  - Body: `{ "enabled": true | false }`
  - On **enable**: publishes `LOCKED` to `door`, `0` to `lb1`/`light-pwm`, `0,0,0` to `rgb`
  - On **disable**: only clears the flag; device states are not restored automatically

- `GET /api/modes/automation`
  - Auth: Required
  - Returns `{ name, automation_mode, door_auto_lock, door_auto_lock_delay_sec }`

- `PUT /api/modes/automation`
  - Auth: Required (homeowner only)
  - Body (all fields optional):
    ```json
    {
      "enabled": true,
      "door_auto_lock": true,
      "door_auto_lock_delay_sec": 120
    }
    ```
  - `door_auto_lock_delay_sec` minimum: 10 seconds

### Automation Rules

Rules fire at a scheduled `time_of_day` on selected `days_of_week` and publish `value` to the target device via Adafruit IO. The background poller (every 5 s) executes matching rules; each rule fires once per minute.

**Away mode overrides automation** — if `away_mode` is on, automation rules are suspended.

**Motion sensor (PIR) is excluded from automation** — it should remain always ON.

**Door states**: `OPEN` | `CLOSE` | `LOCKED`

- `GET /api/automation/rules`
  - Auth: Required
  - Returns rules for the user's current setting profile

- `POST /api/automation/rules`
  - Auth: Required (homeowner only)
  - Body:
    ```json
    {
      "feed_key": "lb1",
      "value": "1",
      "time_of_day": "07:00",
      "days_of_week": ["MON", "TUE", "WED", "THU", "FRI"],
      "enabled": true
    }
    ```
  - `feed_key`: device feed key string (e.g. `lb1`, `door`, `rgb`, `light-pwm`)
  - `time_of_day` format: `"HH:MM"` in server local time (UTC by default)
  - `days_of_week`: JSON array `["MON","WED"]` or comma-separated string `"Mon,Wed,Fri"`; valid values: `MON TUE WED THU FRI SAT SUN`
  - Device value examples:
    - Door: `"OPEN"` / `"CLOSE"` / `"LOCKED"`
    - Light bulb (lb1): `"1"` = ON, `"0"` = OFF
    - Dimmer (light-pwm): `"0"`–`"100"`
    - RGB: `"R,G,B"` e.g. `"255,100,0"`

- `PUT /api/automation/rules/{rule_id}`
  - Auth: Required (homeowner only)
  - Body: any subset of `{ value, time_of_day, days_of_week, enabled }`

- `DELETE /api/automation/rules/{rule_id}`
  - Auth: Required (homeowner only)

- `POST /api/setting-profiles/current/away-mode`
  - Auth: `auth_token` in request body
  - Body:
    ```json
    {
      "auth_token": "<jwt>"
    }
    ```
  - Returns current profile away-mode status.
  - Response `data`:
    - `setting_profile_id`
    - `away_mode`

- `PUT /api/setting-profiles/current/away-mode`
  - Auth: `auth_token` in request body
  - Body:
    ```json
    {
      "auth_token": "<jwt>",
      "away_mode": true
    }
    ```
  - Behavior:
    - updates `away_mode` on current setting profile
  - Response `data`: `true` when updated

### System & Alerts
- `GET /api/alerts/list?since=<ISO_DATETIME>&feed_key=<FEED_KEY>`
  - `since` is optional
  - `feed_key` is optional (`temperature`, `gas`, `pir`, ...)
  - if `feed_key` is set: return only alerts of that feed
  - if `feed_key` is not set: return alerts of all feeds

---

## Current Database Highlights

### `setting_profiles`
Includes threshold defaults:
- `temp_lower_threshold DEFAULT 15.0`
- `temp_upper_threshold DEFAULT 35.0`
- `humidity_lower_threshold DEFAULT 30.0`
- `humidity_upper_threshold DEFAULT 70.0`
- `gas_upper_threshold DEFAULT 800.0`
- `light_lower_threshold DEFAULT 20.0`

### `alerts`
Columns:
- `id`
- `alert_type`
- `feed_key`
- `message`
- `created_at`

### `devices`
Columns:
- `id`
- `feed_key`
- `name`
- `type`
- `status`
- `value`
- `last_record_time`
- `location` *(nullable)*

### `sensors`
Columns:
- `id`
- `feed_key`
- `name`
- `type`
- `unit`
- `current_value`
- `last_recorded_at`
- `location` *(nullable)*

### `sensor_data`
Columns:
- `id` (PK)
- `timestamp`
- `feed_key`
- `value`

`sensor_data.timestamp` is poll-write time (`NOW()`), so each polling cycle appends a new row even if value is unchanged.

---

## Changelog

### 2026-05-22 (automation rules bugfixes)
- `POST /api/automation/rules`: changed body field from `device_id` (integer) to `feed_key` (string); the route now resolves the device internally. This matches what the mobile client sends.
- `POST /api/automation/rules`: `days_of_week` now accepts both a JSON array (`["MON","WED"]`) and a comma-separated string (`"Mon,Wed,Fri"`).
- Fixed SQL syntax in `create_automation_rule` and `update_automation_rule`: replaced `:param::TIME` (broken under SQLAlchemy `text()`) with `CAST(:param AS TIME)`.
- Fixed `PUT /api/automation/rules/{rule_id}` and `DELETE /api/automation/rules/{rule_id}` returning 403 "Rule does not belong to your profile": IDs from `_rule_row_to_dict` are stringified (big-integer safety), so the ownership check now uses `str(rule["setting_profile_id"]) != str(profile_id)`.

### 2026-05-22 (profile name in responses)
- `name` (already a column in `setting_profiles`) is now returned by: `GET /api/system/mode`, `GET /api/modes/away`, `GET /api/modes/automation`, `POST /api/setting-profiles/current/thresholds`, `PUT /api/setting-profiles/current/thresholds`. No migration needed.

### 2026-05-22 (modes & automation)
- New `automation_rules` table (recurring device schedule: `time_of_day TIME`, `days_of_week TEXT`, `value`, `enabled`).
- New `setting_profiles` columns: `automation_mode BOOLEAN`, `door_auto_lock BOOLEAN`, `door_auto_lock_delay_sec INTEGER DEFAULT 120`.
- Implemented `GET /api/system/mode` (was stub) — returns all four mode flags.
- Added `GET/PUT /api/modes/away` — away mode toggle; enabling immediately commands door=LOCKED and all lights off.
- Added `GET/PUT /api/modes/automation` — automation mode toggle + door auto-lock config.
- Added `GET/POST/PUT/DELETE /api/automation/rules` — full CRUD for recurring device schedules.
- Updated `device_polling_worker`: when `automation_mode=TRUE` and `away_mode=FALSE`, executes matching rules each poll cycle and auto-locks door after configured delay.
- Run on existing DBs:
  ```sql
  ALTER TABLE setting_profiles ADD COLUMN IF NOT EXISTS automation_mode BOOLEAN NOT NULL DEFAULT FALSE;
  ALTER TABLE setting_profiles ADD COLUMN IF NOT EXISTS door_auto_lock BOOLEAN NOT NULL DEFAULT FALSE;
  ALTER TABLE setting_profiles ADD COLUMN IF NOT EXISTS door_auto_lock_delay_sec INTEGER NOT NULL DEFAULT 120;
  CREATE TABLE IF NOT EXISTS automation_rules (
      id SERIAL PRIMARY KEY,
      setting_profile_id INTEGER NOT NULL REFERENCES setting_profiles(id) ON DELETE CASCADE,
      device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
      value TEXT NOT NULL,
      time_of_day TIME NOT NULL,
      days_of_week TEXT NOT NULL,
      enabled BOOLEAN NOT NULL DEFAULT TRUE
  );
  CREATE INDEX IF NOT EXISTS automation_rules_profile_idx ON automation_rules (setting_profile_id);
  CREATE INDEX IF NOT EXISTS automation_rules_device_idx ON automation_rules (device_id);
  ```

### 2026-05-22
- `POST /api/auth/register` now sets `house_owner_id` to the registering homeowner's id on the created family member account.
- Added `DELETE /api/users/{user_id}` — homeowner can delete a family member; deleting the homeowner account is blocked.
- Added `PUT /api/auth/change-password` — authenticated users can change their own password with strength validation.
- Implemented `GET /api/users` (was a stub) — returns all household users with `id`, `username`, and `role` (`homeowner` / `family_member`).
- Added `PATCH /api/devices/{device_id}` — homeowner can update a device's `name` and/or `location`.
- Added `PATCH /api/sensors/{sensor_id}` — homeowner can update a sensor's `name` and/or `location`.
- Added corresponding database helpers: `update_user_password`, `list_all_users`, `update_device_info`, `update_sensor_info`.
- Updated Postman collection with all four new requests.

### 2026-05-21
- Added `location VARCHAR(100)` column to both `devices` and `sensors` tables in the DB schema (`db/init/init.sql`).
- Updated `GET /api/devices` to return `location` per device.
- Updated `GET /api/sensors` to return `location` per sensor.
- Both use a dynamic column check (`_get_table_columns`) so existing databases without the column return `null` instead of erroring. Run `ALTER TABLE devices ADD COLUMN location VARCHAR(100)` and `ALTER TABLE sensors ADD COLUMN location VARCHAR(100)` on existing instances to apply the change without re-initialising the DB.

---

## Error Codes
- `400` invalid input
- `401` invalid or missing auth token
- `403` forbidden
- `404` not found
- `422` validation error
- `500` server error
- `502` upstream Adafruit error
