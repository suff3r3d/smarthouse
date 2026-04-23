SENSOR_FEEDS = {
    "temperature",
    "humidity",
    "rain",
    "gas",
    "themis",
}

DEVICE_FEEDS = {
    "door",
    "lb1",
    "pir",
    "rgb",
    "light-pwm",
}


def is_sensor_feed(feed_key: str) -> bool:
    return feed_key in SENSOR_FEEDS


def is_device_feed(feed_key: str) -> bool:
    return feed_key in DEVICE_FEEDS
