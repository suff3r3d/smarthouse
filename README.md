# Smart Home System API Endpoints

This document lists the endpoints currently coded in the backend.

## Response Format (Universal)
All JSON APIs return:
- Success: `{ "success": true, "data": ... }`
- Failure: `{ "success": false, "message": "..." }`

## Auth Token Input
The middleware accepts JWT from:
- Header `auth-token: <token>`
- Header `Authorization: Bearer <token>`
- JSON body field `auth_token` (for JSON requests)

## 1. App Health / Utility
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| GET | `/` | Health check for FastAPI server | None | `success=true` -> `data` object |
| GET | `/get-user-by-username` | Get user by username | **Query:** `username` (string) | `success=true` -> `data` user object |
| GET | `/api/hello` | Simple API router health check | None | `success=true` -> `data` object |

## 2. Authentication
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| POST | `/api/auth/register` | Register a new user | **Body:** `{ "username": "string", "password": "string", "is_house_owner": false }` | Success message in `data`; errors in `message` |
| POST | `/api/auth/login` | Login and return JWT token | **Body:** `{ "username": "string", "password": "string" }` | `success=true` -> `data.access_token`, `data.token_type` |

## 3. Users
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| GET | `/api/users` | List users (stub/not implemented yet) | None | Stub; currently returns failure or empty success wrapper depending implementation |

## 4. Sensors
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| GET | `/api/sensors` | List sensors from database (`sensors` table) | None | `success=true` -> `data.sensors`, `data.count` |
| GET | `/api/sensors/{sensor_id}/get_value` | Get current sensor value from database | Auth required (`auth-token` header, Bearer token, or JSON `auth_token`) | `success=true` -> `data` raw sensor value |
| GET | `/api/sensors/latest` | Get latest sensor data (stub) | None | Stub; currently returns failure or empty success wrapper depending implementation |
| GET | `/api/sensors/history` | Get sensor history (stub) | None | Stub; currently returns failure or empty success wrapper depending implementation |
<!-- | GET | `/api/sensors/export` | Export sensor history (stub) | None | Stub | -->

## 5. Devices
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| GET | `/api/devices` | List controllable device feeds from Adafruit IO | None | `success=true` -> `data.devices`, `data.count` |
| POST | `/api/devices/{device_id}/set_state` | Set device state (device feeds only) | **Body:** `{ "auth_token": "string", "state": "string \| number \| boolean \| object" }` | `success=true` -> update result in `data` |
| POST | `/api/devices/{device_id}/get_state` | Get current device state value only | **Body:** `{ "auth_token": "string" }` | `success=true` -> `data` raw device value |

## 6. Schedules
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| GET | `/api/schedules` | List schedules for authenticated user's profiles | **Body (optional for auth):** `{ "auth_token": "string" }`<br>**Query (optional):** `device_id` (int) | `success=true` -> `data` schedule list |
| POST | `/api/schedules` | Create a new schedule | **Body:** `{ "auth_token": "string", "setting_profile_id": 1, "device_id": 1, "action": "TURN_ON" \| "TURN_OFF" \| "SET_VALUE", "payload": { ... }, "trigger_time": "YYYY-MM-DDTHH:MM:SS" }` | `success=true` -> `data` created schedule |
| GET | `/api/schedules/{schedule_id}` | Get one schedule | **Body (optional for auth):** `{ "auth_token": "string" }` | `success=true` -> `data` schedule object |
| PUT | `/api/schedules/{schedule_id}` | Update one schedule | **Body:** `{ "auth_token": "string", "setting_profile_id"?: 1, "device_id"?: 1, "action"?: "TURN_ON" \| "TURN_OFF" \| "SET_VALUE", "payload"?: { ... }, "trigger_time"?: "YYYY-MM-DDTHH:MM:SS" }` | `success=true` -> `data` updated schedule |

## 7. Alerts
| Method | Endpoint | Description | Parameters / Body | Response Format |
|--------|----------|-------------|-------------------|-----------------|
| GET | `/api/alerts/list` | List alerts from database | **Query (optional):** `since` (ISO datetime, e.g. `2026-05-03T07:30:00Z`) | `success=true` -> `data.alerts`, `data.count` |

## Notes
- Device polling worker syncs latest Adafruit feed values into both `devices` and `sensors` tables by `feed_key`.
- Sensors are read-only; device mutation is limited to controllable feeds (`door`, `lb1`, `pir`, `rgb`, `light-pwm`).
- DB init seeds a default `admin` user with password `admin` (bcrypt hash in `db/init/init.sql`).
- Several endpoints are route stubs (`pass`) and are listed to reflect what is currently coded.

# Notes
Them loai alert (type: (warining), title, msg, timestamp (hour, minute, second, day))
