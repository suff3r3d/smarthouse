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

### Users
- `GET /api/users` (stub)

### Devices
- `GET /api/devices`
  - Reads current device states from database cache

- `POST /api/devices/{device_id}/set_state`
  - Body: `{ "auth_token": "...", "state": <any> }`
  - Publishes value to Adafruit feed

- `GET /api/devices/{device_id}/get_state`
  - Body model still expects `auth_token` in current code
  - Returns cached device state from database

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

- `GET /api/sensors/latest` (stub)
- `GET /api/sensors/export` (stub)

### Schedules

- `GET /api/schedules`
  - Auth: Required
  - Query (optional): `device_id` (integer)
  - Returns schedules that belong to authenticated user’s setting profiles.
  - Response `data` shape: array of schedule objects
    - `id`
    - `setting_profile_id`
    - `device_id`
    - `value` (string)
    - `trigger_time` (ISO datetime)

- `POST /api/schedules`
  - Auth: `auth_token` in request body (house-owner only)
  - Body:
    ```json
    {
      "auth_token": "<jwt>",
      "device_id": 2,
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
      "device_id": 2,
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
  - Response `data`: full updated thresholds object

### System & Alerts
- `GET /api/system/mode` (stub)
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

### `sensor_data`
Columns:
- `id` (PK)
- `timestamp`
- `feed_key`
- `value`

`sensor_data.timestamp` is poll-write time (`NOW()`), so each polling cycle appends a new row even if value is unchanged.

---

## Error Codes
- `400` invalid input
- `401` invalid or missing auth token
- `403` forbidden
- `404` not found
- `422` validation error
- `500` server error
- `502` upstream Adafruit error
