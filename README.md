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

- `GET /api/sensors/latest` (stub)
- `GET /api/sensors/export` (stub)

### Schedules
- `GET /api/schedules`
- `POST /api/schedules`
- `GET /api/schedules/{schedule_id}`
- `PUT /api/schedules/{schedule_id}`

Current schedule payload shape:
- `setting_profile_id`
- `device_id`
- `action` (`TURN_ON` | `TURN_OFF` | `SET_VALUE`)
- `payload` (optional JSON)
- `trigger_time`

### System & Alerts
- `GET /api/system/mode` (stub)
- `GET /api/alerts/list?since=<ISO_DATETIME>`
  - `since` is optional
  - Returns recent alerts from DB

---

## Current Database Highlights

### `setting_profiles`
Includes threshold defaults:
- `temp_lower_threshold DEFAULT 15.0`
- `temp_upper_threshold DEFAULT 35.0`
- `gas_upper_threshold DEFAULT 800.0`

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

