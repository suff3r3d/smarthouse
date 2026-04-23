import os
import asyncio
import httpx
from typing import Optional, List, Dict, Any

class AdafruitIO:
    def __init__(self):
        self.username = os.getenv("AIO_USERNAME")
        self.key = os.getenv("AIO_KEY")
        if not self.username or not self.key:
            raise ValueError("AIO_USERNAME and AIO_KEY must be set in environment variables")
        self.base_url = "https://io.adafruit.com/api/v2"
        self.headers = {"X-AIO-Key": self.key, "Content-Type": "application/json"}

    async def publish_feed(self, feed_key: str, value: Any) -> dict:
        url = f"{self.base_url}/{self.username}/feeds/{feed_key}/data"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json={"value": str(value)})
            response.raise_for_status()
            return response.json()

    async def get_feed_value(self, feed_key: str) -> Optional[Any]:
        url = f"{self.base_url}/{self.username}/feeds/{feed_key}/data/last"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json().get("value")
            except httpx.HTTPStatusError:
                return None

    async def get_feed_history(self, feed_key: str, limit: int = 30) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{self.username}/feeds/{feed_key}/data"
        params = {"limit": limit}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                # Assuming created_at and value exist, similar to the JS version
                return [
                    {
                        "value": float(d.get("value", 0)),
                        "time": d.get("created_at"),
                    }
                    for d in reversed(response.json())
                ]
            except httpx.HTTPStatusError:
                return []

    async def get_all_devices(self) -> List[Dict[str, Any]]:
        """
        Return every feed as a device record with its most recent value.

        Adafruit IO exposes feeds as the primary resource, so the app treats
        feeds as device entries and enriches each one with its latest data point.
        """
        feeds_url = f"{self.base_url}/{self.username}/feeds"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(feeds_url, headers=self.headers)
                response.raise_for_status()
                feeds = response.json()
            except httpx.HTTPStatusError:
                return []

            async def enrich_feed(feed: Dict[str, Any]) -> Dict[str, Any]:
                feed_key = feed.get("key")
                if not feed_key:
                    return {**feed, "last_value": None, "last_data": None}

                last_url = f"{feeds_url}/{feed_key}/data/last"
                try:
                    last_response = await client.get(last_url, headers=self.headers)
                    if last_response.status_code == 404:
                        last_data = None
                    else:
                        last_response.raise_for_status()
                        last_data = last_response.json()
                except httpx.HTTPStatusError:
                    last_data = None

                return {
                    **feed,
                    "last_value": last_data.get("value") if last_data else None,
                    "last_data": last_data,
                }

            return await asyncio.gather(*(enrich_feed(feed) for feed in feeds))

# Feed keys for convenience
# Sensor (Arduino → App)
FEED_TEMPERATURE = 'temperature'
FEED_HUMIDITY    = 'humidity'
FEED_THEMIS      = 'themis'
FEED_GAS         = 'gas'
FEED_RAIN        = 'rain'

# Control (App → Arduino)
FEED_LB1   = 'lb1'
FEED_RGB   = 'rgb'
FEED_DOOR  = 'door'
FEED_PIR   = 'pir'
