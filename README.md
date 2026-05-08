# Smart House Backend API

A FastAPI backend for a smart home system that integrates with Adafruit IO to control devices and read sensor data. Supports user authentication, device control, sensor monitoring, and scheduled automation.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Running with Docker](#running-with-docker)
  - [Running Locally](#running-locally)
- [Authentication](#authentication)
- [Response Format](#response-format)
- [API Reference](#api-reference)
  - [Health & Utility](#health--utility)
  - [Authentication Endpoints](#authentication-endpoints)
  - [Users](#users)
  - [Sensors](#sensors)
  - [Devices](#devices)
  - [Schedules](#schedules)
  - [System & Alerts](#system--alerts)
- [Data Models](#data-models)
- [Database Schema](#database-schema)
- [Adafruit IO Integration](#adafruit-io-integration)
- [Error Codes](#error-codes)

---

## Tech Stack

| Layer           | Technology                      |
| --------------- | ------------------------------- |
| Framework       | FastAPI (Python 3.12)           |
| Server          | Uvicorn (ASGI)                  |
| ORM             | SQLAlchemy 2.0 (async)          |
| Database        | PostgreSQL (TLS via `root.crt`) |
| Auth            | JWT (HS256, 30 min expiry)      |
| IoT Integration | Adafruit IO REST API            |
| Deployment      | Docker + Docker Compose         |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose installed, **or** Python 3.12+ for local development
- An [Adafruit IO](https://io.adafruit.com) account with feeds configured
- `root.crt` placed in the project root (mounted for PostgreSQL SSL — required for managed/cloud DB connections)

### Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/smarthouse
AIO_USERNAME=your_adafruit_io_username
AIO_KEY=your_adafruit_io_key
JWT_SECRET=a-long-random-secret-string
```

| Variable       | Description                                   | Required |
| -------------- | --------------------------------------------- | -------- |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg driver) | Yes      |
| `AIO_USERNAME` | Adafruit IO account username                  | Yes      |
| `AIO_KEY`      | Adafruit IO API key                           | Yes      |
| `JWT_SECRET`   | Secret key for signing JWT tokens             | Yes      |

### Running with Docker

```bash
docker compose up --build t
```

The API will be available at `http://localhost:8001`.

Interactive API docs (Swagger UI) are at `http://localhost:8001/docs`.

> `root.crt` is automatically mounted into the container at `/root/.postgresql/root.crt` for PostgreSQL TLS.

### Running Locally

```bash
cd backend
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/smarthouse"
export AIO_USERNAME="your_aio_username"
export AIO_KEY="your_aio_key"
export JWT_SECRET="your-secret-key"

uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Authentication

The API uses **JWT Bearer tokens**. Obtain a token by calling `POST /api/auth/login`, then pass it with subsequent requests in one of three ways:

**Option 1 — Authorization header (preferred):**

```http
Authorization: Bearer <token>
```

**Option 2 — Custom header:**

```http
auth-token: <token>
```

**Option 3 — Request body field (for select endpoints):**

```json
{ "auth_token": "<token>" }
```

Tokens expire after **30 minutes**.

### Authorization Levels

| Level         | Who                              | Capabilities                                 |
| ------------- | -------------------------------- | -------------------------------------------- |
| Public        | Anyone                           | Register, login, list devices/sensors        |
| Authenticated | Any valid JWT user               | Get sensor/device values, read own schedules |
| House Owner   | User with `is_house_owner: true` | Create and update schedules                  |

---

## Response Format

All JSON responses are wrapped by the middleware:

- **Success:** `{ "success": true, "data": <payload> }`
- **Failure:** `{ "success": false, "message": "<error>" }`

Endpoints that already return a `success`/`data`/`message` shaped object are passed through as-is.

---

## API Reference

Base URL: `http://localhost:8001`

---

### Health & Utility

#### `GET /`

Server health check.

**Response `200`:**

```json
{
  "success": true,
  "data": { "message": "Smart House FastAPI server is running!" }
}
```

---

#### `GET /get-user-by-username`

Look up a user by their username.

**Query Parameters:**

| Parameter  | Type   | Description         |
| ---------- | ------ | ------------------- |
| `username` | string | Username to look up |

**Response `200`:**

```json
{
  "success": true,
  "data": { "id": 1, "username": "alice", "is_house_owner": true }
}
```

---

#### `GET /api/hello`

API router health check.

**Response `200`:**

```json
{ "success": true, "data": { "message": "Hello from the API router!" } }
```

---

### Authentication Endpoints

#### `POST /api/auth/register`

Register a new user account.

**Request Body:**

```json
{
  "username": "alice",
  "password": "securepassword",
  "is_house_owner": false
}
```

| Field            | Type    | Required | Description                             |
| ---------------- | ------- | -------- | --------------------------------------- |
| `username`       | string  | Yes      | Unique username                         |
| `password`       | string  | Yes      | Plaintext password (hashed with bcrypt) |
| `is_house_owner` | boolean | No       | Defaults to `false`                     |

**Response `200`:**

```json
{ "success": true, "data": { "message": "User registered successfully" } }
```

**Errors:**

- `400` — Username already exists

---

#### `POST /api/auth/login`

Authenticate a user and receive a JWT token.

**Request Body:**

```json
{
  "username": "alice",
  "password": "securepassword"
}
```

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

**Errors:**

- `401` — Invalid username or password

---

### Users

#### `GET /api/users`

List all users.

> **Status: Not yet implemented (stub).**

---

### Sensors

Sensors are **read-only** feeds pulled from Adafruit IO and cached in the database. Supported sensor feed keys: `temperature`, `humidity`, `rain`, `gas`, `themis`.

---

#### `GET /api/sensors`

List all sensor feeds and their latest cached values from the database.

**Auth:** Not required

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "sensors": [
      {
        "feed_key": "temperature",
        "name": "Temperature",
        "current_value": "28.50",
        "last_recorded_at": "2026-04-26T10:00:00Z"
      }
    ],
    "count": 5
  }
}
```

---

#### `GET /api/sensors/{sensor_id}/get_value`

Get the current cached value of a specific sensor.

**Auth:** Required (JWT via header or body)

**Path Parameters:**

| Parameter   | Type   | Description                                      |
| ----------- | ------ | ------------------------------------------------ |
| `sensor_id` | string | Sensor feed key (e.g. `temperature`, `humidity`) |

**Response `200`:**

```json
{ "success": true, "data": "28.00" }
```

**Errors:**

- `400` — `sensor_id` is not a valid sensor feed key
- `401` — Missing or invalid token
- `404` — No stored value found for this sensor

---

#### `GET /api/sensors/latest`

Get the latest reading for all sensors.

> **Status: Not yet implemented (stub).**

---

#### `GET /api/sensors/history`

Get historical readings for sensors.

> **Status: Not yet implemented (stub).**

---

#### `GET /api/sensors/export`

Export sensor history as a file (e.g. CSV).

> **Status: Not yet implemented (stub).**

---

### Devices

Devices are **controllable** feeds on Adafruit IO. Supported device feed keys: `door`, `lb1`, `pir`, `rgb`, `light-pwm`.

---

#### `GET /api/devices`

List all controllable device feeds and their current cached states.

**Auth:** Not required

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "devices": [
      {
        "feed_key": "lb1",
        "name": "Light Bulb 1",
        "value": "ON",
        "last_record_time": "2026-04-26T09:30:00Z"
      }
    ],
    "count": 5
  }
}
```

---

#### `POST /api/devices/{device_id}/get_state`

Get the current cached state of a specific device.

**Auth:** Required (JWT in body)

**Path Parameters:**

| Parameter   | Type   | Description                          |
| ----------- | ------ | ------------------------------------ |
| `device_id` | string | Device feed key (e.g. `lb1`, `door`) |

**Request Body:**

```json
{ "auth_token": "<jwt-token>" }
```

**Response `200`:**

```json
{ "success": true, "data": "ON" }
```

**Errors:**

- `400` — `device_id` is not a controllable device feed
- `401` — Missing or invalid token
- `404` — No stored value found for this device

---

#### `POST /api/devices/{device_id}/set_state`

Set the state of a specific device by publishing to its Adafruit IO feed.

**Auth:** Required (JWT in body)

**Path Parameters:**

| Parameter   | Type   | Description                          |
| ----------- | ------ | ------------------------------------ |
| `device_id` | string | Device feed key (e.g. `lb1`, `door`) |

**Request Body:**

```json
{
  "auth_token": "<jwt-token>",
  "state": "ON"
}
```

| Field        | Type                                  | Description                             |
| ------------ | ------------------------------------- | --------------------------------------- |
| `auth_token` | string                                | JWT token                               |
| `state`      | string \| number \| boolean \| object | New value to publish to the device feed |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "message": "Device state updated successfully",
    "device_id": "lb1",
    "state": "ON",
    "data": { "value": "ON", "created_at": "2026-04-26T10:05:00Z" }
  }
}
```

**Errors:**

- `400` — `device_id` is not a controllable device feed
- `401` — Missing or invalid token
- `502` — Adafruit IO unavailable

---

### Schedules

Schedules automate device actions at a specific time. Schedules belong to a **setting profile**, which belongs to a user.

---

#### `GET /api/schedules`

List all schedules for the authenticated user's setting profiles.

**Auth:** Required (JWT via header or body)

**Query Parameters:**

| Parameter   | Type    | Required | Description                   |
| ----------- | ------- | -------- | ----------------------------- |
| `device_id` | integer | No       | Filter schedules by device ID |

**Response `200`:**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "setting_profile_id": 2,
      "device_id": 3,
      "action": "TURN_ON",
      "payload": null,
      "trigger_time": "2026-04-27T07:00:00Z"
    }
  ]
}
```

---

#### `POST /api/schedules`

Create a new schedule.

**Auth:** Required (JWT, house owner only)

**Request Body:**

```json
{
  "setting_profile_id": 2,
  "device_id": 3,
  "action": "TURN_ON",
  "payload": { "brightness": 80 },
  "trigger_time": "2026-04-27T07:00:00"
}
```

| Field                | Type     | Required | Description                                           |
| -------------------- | -------- | -------- | ----------------------------------------------------- |
| `setting_profile_id` | integer  | Yes      | ID of the setting profile this schedule belongs to    |
| `device_id`          | integer  | Yes      | ID of the device to act on                            |
| `action`             | string   | Yes      | One of: `TURN_ON`, `TURN_OFF`, `SET_VALUE`            |
| `payload`            | object   | No       | Extra metadata for the action (e.g. brightness value) |
| `trigger_time`       | datetime | Yes      | When to execute the action (ISO 8601)                 |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "id": 5,
    "setting_profile_id": 2,
    "device_id": 3,
    "action": "TURN_ON",
    "payload": { "brightness": 80 },
    "trigger_time": "2026-04-27T07:00:00Z"
  }
}
```

**Errors:**

- `400` — Invalid schedule payload
- `401` — Missing or invalid token
- `403` — User is not the house owner
- `403` — Setting profile does not belong to this user

---

#### `GET /api/schedules/{schedule_id}`

Get a single schedule by ID.

**Auth:** Required (JWT via header or body)

**Path Parameters:**

| Parameter     | Type    | Description |
| ------------- | ------- | ----------- |
| `schedule_id` | integer | Schedule ID |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "id": 5,
    "setting_profile_id": 2,
    "device_id": 3,
    "action": "TURN_ON",
    "payload": null,
    "trigger_time": "2026-04-27T07:00:00Z"
  }
}
```

**Errors:**

- `401` — Missing or invalid token
- `403` — Schedule does not belong to this user
- `404` — Schedule not found

---

#### `PUT /api/schedules/{schedule_id}`

Update an existing schedule. All body fields are optional.

**Auth:** Required (JWT, house owner only)

**Path Parameters:**

| Parameter     | Type    | Description |
| ------------- | ------- | ----------- |
| `schedule_id` | integer | Schedule ID |

**Request Body:**

```json
{
  "action": "TURN_OFF",
  "trigger_time": "2026-04-27T22:00:00"
}
```

**Response `200`:** Updated schedule object (same shape as `GET /api/schedules/{schedule_id}`).

**Errors:**

- `401` — Missing or invalid token
- `403` — User is not the house owner
- `403` — Schedule or new `setting_profile_id` does not belong to this user
- `404` — Schedule not found

---

### System & Alerts

#### `GET /api/system/mode`

Get the current system mode (e.g. Home / Away).

> **Status: Not yet implemented (stub).**

---

#### `GET /api/alerts/list`

List recent system alerts.

**Auth:** Not required

**Query Parameters:**

| Parameter | Type                | Required | Description                                                                   |
| --------- | ------------------- | -------- | ----------------------------------------------------------------------------- |
| `since`   | datetime (ISO 8601) | No       | Only return alerts created after this timestamp (e.g. `2026-05-03T07:30:00Z`) |

**Response `200`:**

```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": 1,
        "device_id": 2,
        "message": "Temperature exceeded threshold",
        "created_at": "2026-05-03T08:00:00Z"
      }
    ],
    "count": 1
  }
}
```

> **Planned fields:** alert `type` (e.g. `warning`), `title`, and structured `timestamp` (hour, minute, second, day).

---

## Data Models

### User

```
id                          integer (PK)
username                    string (unique)
password_hash               string
is_house_owner              boolean
current_setting_profile_id  integer (FK → setting_profiles)
```

### Setting Profile

```
id                   integer (PK)
user_id              integer (FK → users, cascade delete)
name                 string
temp_upper_threshold float (optional)
temp_lower_threshold float (optional)
away_mode            boolean
```

### Device

```
id               integer (PK)
feed_key         string (unique) — Adafruit IO feed key
name             string (unique)
type             enum: DOOR | LIGHT | MOTION | RGB | DIMMER | GENERIC
status           enum: ONLINE | OFFLINE | ERROR
value            string (last known state)
last_record_time timestamp
```

### Sensor

```
id               integer (PK)
feed_key         string (unique) — Adafruit IO feed key
name             string (unique)
type             enum: TEMPERATURE | HUMIDITY | RAIN | GAS | LIGHT_INTENSITY | GENERIC
current_value    string
last_recorded_at timestamp
```

### Schedule

```
id                   integer (PK)
setting_profile_id   integer (FK → setting_profiles, cascade delete)
device_id            integer (FK → devices, cascade delete)
action               enum: TURN_ON | TURN_OFF | SET_VALUE
payload              jsonb (optional extra data)
trigger_time         timestamp
```

### Alert

```
id          integer (PK)
device_id   integer (FK → devices, nullable)
message     text
created_at  timestamp
```

---

## Database Schema

The PostgreSQL schema is initialized automatically on first start from `db/init/init.sql`.

A default `admin` account is seeded with password `admin` (bcrypt-hashed).

**Pre-seeded devices** (mapped to Adafruit IO feeds):

| Feed Key    | Name          | Type   |
| ----------- | ------------- | ------ |
| `door`      | Front Door    | DOOR   |
| `lb1`       | Light Bulb 1  | LIGHT  |
| `light-pwm` | Dimmer Light  | DIMMER |
| `pir`       | Motion Sensor | MOTION |
| `rgb`       | RGB Light     | RGB    |

**Pre-seeded sensors** (mapped to Adafruit IO feeds):

| Feed Key      | Name        | Type        |
| ------------- | ----------- | ----------- |
| `temperature` | Temperature | TEMPERATURE |
| `humidity`    | Humidity    | HUMIDITY    |
| `rain`        | Rain        | RAIN        |
| `gas`         | Gas         | GAS         |
| `themis`      | Themis      | GENERIC     |

---

## Adafruit IO Integration

All real-time device and sensor data flows through the [Adafruit IO REST API](https://io.adafruit.com/api/docs/).

- **Base URL:** `https://io.adafruit.com/api/v2`
- **Auth:** `X-AIO-Key` request header

The backend polls all device and sensor feeds every **60 seconds** in a background thread (`device_polling_worker`) to keep the local database state current.

**Operations:**

- `publish_feed(feed_key, value)` — Write a new value to a device feed
- `get_feed_value(feed_key)` — Read the latest value from any feed
- `get_feed_history(feed_key, limit=30)` — Retrieve up to 30 historical data points
- `get_all_devices()` — List all feeds with their latest data

---

## Error Codes

| Code  | Meaning                                               |
| ----- | ----------------------------------------------------- |
| `400` | Bad request — invalid input or constraint violation   |
| `401` | Unauthorized — missing or expired JWT token           |
| `403` | Forbidden — insufficient permissions                  |
| `404` | Not found — resource does not exist                   |
| `422` | Unprocessable entity — request body validation failed |
| `500` | Internal server error                                 |
| `502` | Bad gateway — Adafruit IO is unreachable              |
