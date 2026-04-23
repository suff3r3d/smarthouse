# Smart Home System API Endpoints

This document lists the endpoints currently coded in the backend.

## 1. App Health / Utility
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| GET | `/` | Health check for FastAPI server | None |
| GET | `/get-user-by-username` | Get user by username | **Query:** `username` (string) |
| GET | `/api/hello` | Simple API router health check | None |

## 2. Authentication
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| POST | `/api/auth/register` | Register a new user | **Body:** `{ "username": "string", "password": "string", "is_house_owner": false }` |
| POST | `/api/auth/login` | Login and return JWT token | **Body:** `{ "username": "string", "password": "string" }` |

## 3. Users
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| GET | `/api/users` | List users (stub/not implemented yet) | None |

## 4. Sensors
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| GET | `/api/sensors` | List sensor feeds from Adafruit IO (read-only) | None |
| POST | `/api/sensors/{sensor_id}/get_value` | Get current sensor value only | **Body:** `{ "auth_token": "string" }`<br>**Response:** raw value only (e.g. `"28.00"`) |
| GET | `/api/sensors/latest` | Get latest sensor data (stub) | None |
| GET | `/api/sensors/history` | Get sensor history (stub) | None |
| GET | `/api/sensors/export` | Export sensor history (stub) | None |

## 5. Devices
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| GET | `/api/devices` | List controllable device feeds from Adafruit IO | None |
| POST | `/api/devices/{device_id}/set_state` | Set device state (device feeds only) | **Body:** `{ "auth_token": "string", "state": "string \| number \| boolean \| object" }` |
| POST | `/api/devices/{device_id}/get_state` | Get current device state value only | **Body:** `{ "auth_token": "string" }`<br>**Response:** raw value only (e.g. `"28.00"`) |

## 6. Schedules
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| GET | `/api/schedules` | List schedules for authenticated user's profiles | **Body:** `{ "auth_token": "string" }`<br>**Query (optional):** `device_id` (int) |
| POST | `/api/schedules` | Create a new schedule | **Body:** `{ "auth_token": "string", "setting_profile_id": 1, "device_id": 1, "action": "TURN_ON" \| "TURN_OFF" \| "SET_VALUE", "payload": { ... }, "trigger_time": "YYYY-MM-DDTHH:MM:SS" }` |
| GET | `/api/schedules/{schedule_id}` | Get one schedule | **Body:** `{ "auth_token": "string" }` |
| PUT | `/api/schedules/{schedule_id}` | Update one schedule | **Body:** `{ "auth_token": "string", "setting_profile_id"?: 1, "device_id"?: 1, "action"?: "TURN_ON" \| "TURN_OFF" \| "SET_VALUE", "payload"?: { ... }, "trigger_time"?: "YYYY-MM-DDTHH:MM:SS" }` |

## 7. System & Alerts
| Method | Endpoint | Description | Parameters / Body |
|--------|----------|-------------|-------------------|
| GET | `/api/system/mode` | Get system mode (stub) | None |
| GET | `/api/alerts` | List alerts (stub) | None |

## Notes
- Auth token is documented in request body as `auth_token` for protected APIs.
- Sensors are read-only; device mutation is limited to controllable feeds (`door`, `lb1`, `pir`, `rgb`, `light-pwm`).
- Several endpoints are route stubs (`pass`) and are listed to reflect what is currently coded.
