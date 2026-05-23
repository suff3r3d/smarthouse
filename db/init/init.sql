DROP TABLE IF EXISTS sensor_data, alerts, schedules, sensors, devices, setting_profiles, users, automation_rules CASCADE;
DROP TYPE IF EXISTS user_role, sensor_type, device_type, device_status, alert_type;

CREATE TYPE device_type AS ENUM ('DOOR', 'LIGHT', 'MOTION', 'RGB', 'DIMMER', 'GENERIC');
CREATE TYPE sensor_type AS ENUM ('TEMPERATURE', 'HUMIDITY', 'RAIN', 'GAS', 'LIGHT_INTENSITY', 'GENERIC');
CREATE TYPE device_status AS ENUM ('ONLINE', 'OFFLINE', 'ERROR');
CREATE TYPE alert_type AS ENUM (
    'WARNING',
    'INTRUSION',
    'DOOR_FORCED_OPEN',
    'MOTION_DETECTED',
    'GAS_LEAK',
    'RAIN_DETECTED',
    'HIGH_TEMPERATURE',
    'LOW_TEMPERATURE',
    'LOW_LIGHT',
    'DEVICE_OFFLINE'
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_house_owner BOOLEAN NOT NULL DEFAULT FALSE,
    current_setting_profile_id INTEGER
);

CREATE TABLE setting_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    temp_lower_threshold FLOAT DEFAULT 15.0,
    temp_upper_threshold FLOAT DEFAULT 35.0,
    humidity_lower_threshold FLOAT DEFAULT 30.0,
    humidity_upper_threshold FLOAT DEFAULT 70.0,
    gas_upper_threshold FLOAT DEFAULT 800.0,
    light_lower_threshold FLOAT DEFAULT 20.0,
    away_mode BOOLEAN NOT NULL DEFAULT FALSE,
    automation_mode BOOLEAN NOT NULL DEFAULT FALSE,
    door_auto_lock BOOLEAN NOT NULL DEFAULT FALSE,
    door_auto_lock_delay_sec INTEGER NOT NULL DEFAULT 120,
    UNIQUE(user_id, name)
);

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    feed_key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) UNIQUE NOT NULL,
    location VARCHAR(100) NOT NULL,
    type device_type NOT NULL,
    status device_status NOT NULL DEFAULT 'OFFLINE',
    value TEXT,
    last_record_time TIMESTAMPTZ
);

CREATE TABLE sensors (
    id SERIAL PRIMARY KEY,
    feed_key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) UNIQUE NOT NULL,
    location VARCHAR(100) NOT NULL,
    type sensor_type NOT NULL,
    unit VARCHAR(32),
    current_value TEXT,
    last_recorded_at TIMESTAMPTZ
);

CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    setting_profile_id INTEGER NOT NULL REFERENCES setting_profiles(id) ON DELETE CASCADE,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    trigger_time TIMESTAMPTZ NOT NULL
);

CREATE TABLE automation_rules (
    id SERIAL PRIMARY KEY,
    setting_profile_id INTEGER NOT NULL REFERENCES setting_profiles(id) ON DELETE CASCADE,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    time_of_day TIME NOT NULL,
    days_of_week TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_type alert_type NOT NULL DEFAULT 'WARNING',
    feed_key VARCHAR(100),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sensor_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    feed_key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL
);

ALTER TABLE users
ADD CONSTRAINT users_current_setting_profile_fkey
FOREIGN KEY (current_setting_profile_id) REFERENCES setting_profiles(id) ON DELETE SET NULL;

CREATE INDEX ON setting_profiles (user_id);
CREATE INDEX ON users (current_setting_profile_id);
CREATE UNIQUE INDEX users_single_house_owner_idx ON users ((is_house_owner)) WHERE is_house_owner = TRUE;
CREATE INDEX ON schedules (setting_profile_id);
CREATE INDEX ON schedules (device_id);
CREATE UNIQUE INDEX schedules_unique_profile_device_idx ON schedules (setting_profile_id, device_id);
CREATE INDEX ON alerts (feed_key);
CREATE INDEX ON sensor_data (feed_key, timestamp DESC);
CREATE INDEX automation_rules_profile_idx ON automation_rules (setting_profile_id);
CREATE INDEX automation_rules_device_idx ON automation_rules (device_id);

-- Seed default admin account (admin:admin).
INSERT INTO users (username, password_hash, is_house_owner) VALUES
    ('admin', '$2b$12$R3dnZHEGxvKkg.ZtvDLwJ.ntf15rLt4wr..RBxlBVpGZfhi1TZ4Km', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Seed a default profile for the admin account.
INSERT INTO setting_profiles (user_id, name, away_mode)
SELECT id, 'Default', FALSE
FROM users
WHERE username = 'admin'
ON CONFLICT (user_id, name) DO NOTHING;

-- Point admin to its default setting profile.
UPDATE users u
SET current_setting_profile_id = sp.id
FROM setting_profiles sp
WHERE u.username = 'admin'
  AND sp.user_id = u.id
  AND sp.name = 'Default';

-- Seed from current Adafruit feed list:
-- Devices (controllable): door, lb1, light-pwm, pir, rgb
INSERT INTO devices (feed_key, name, type, status, value, last_record_time, location) VALUES
    ('door', 'DOOR', 'DOOR', 'ONLINE', 'OPEN', '2026-04-16T09:05:03Z', 'Living room'),
    ('lb1', 'LB1', 'LIGHT', 'ONLINE', '41', '2026-04-16T09:05:07Z', 'Living room'),
    ('light-pwm', 'light_pwm', 'DIMMER', 'ONLINE', NULL, NULL, 'Living room'),
    ('pir', 'PIR', 'MOTION', 'ONLINE', 'ON', '2026-04-16T09:05:03Z', 'Living room'),
    ('rgb', 'RGB', 'RGB', 'ONLINE', '15', '2026-04-16T09:05:09Z', 'Living room');

-- Sensors (read-only): temperature, humidity, rain, gas, themis
INSERT INTO sensors (feed_key, name, type, unit, current_value, last_recorded_at) VALUES
    ('temperature', 'temperature', 'TEMPERATURE', '°C', '28.00', '2026-04-13T06:14:57Z', 'Living room'),
    ('humidity', 'humidity', 'HUMIDITY', '%', '45', '2026-04-13T06:14:58Z', 'Living room'),
    ('rain', 'rain', 'RAIN', 'raw', '716', '2026-04-13T06:14:58Z', 'Living room'),
    ('gas', 'gas', 'GAS', 'ppm', '820', '2026-04-13T06:14:58Z', 'Living room'),
    ('themis', 'themis', 'LIGHT_INTENSITY', '%', '82', '2026-04-13T06:14:58Z', 'Living room');
