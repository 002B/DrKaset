"""
External API fetchers for the offline data-preparation pipeline.

Backend should read the generated FAISS index, not call these fetchers.
"""

from typing import Any

import requests


def fetch_json(url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_openweather(api_key: str, lat: float, lon: float) -> dict[str, Any]:
    return fetch_json(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "th"},
    )
