from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from time import monotonic
from typing import Optional

import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherError(Exception):
    pass

@dataclass
class HourForecast:
    time: str
    temperature_c: float
    precipitation_probability: Optional[float]


@dataclass
class WeatherForecast:
    city: str
    latitude: float
    longitude: float
    retrieved_at: str
    hours: list[HourForecast]
    source: str = "Open-Meteo"


class GeocodingClient:

    def find_city(self, city_name):
        try:
            response = requests.get(
                GEOCODING_URL,
                params={
                    "name": city_name,
                    "count": 1,
                    "language": "uk",
                    "format": "json",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as error:
            raise WeatherError(f"Не вдалося знайти місто через API: {error}") from error
        except ValueError as error:
            raise WeatherError("Сервіс геокодування повернув некоректний JSON.") from error

        results = data.get("results", [])
        if not results:
            raise WeatherError(f"Місто «{city_name}» не знайдено.")

        city = results[0]
        if "latitude" not in city or "longitude" not in city or "name" not in city:
            raise WeatherError("Відповідь геокодування не містить потрібних полів.")

        return city


class ForecastProvider:

    def __init__(self):
        self.http_requests = 0

    def get_forecast(self, latitude, longitude):
        self.http_requests += 1
        try:
            response = requests.get(
                FORECAST_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "hourly": "temperature_2m,precipitation_probability",
                    "forecast_days": 1,
                    "timezone": "auto",
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as error:
            raise WeatherError(f"Не вдалося отримати прогноз: {error}") from error
        except ValueError as error:
            raise WeatherError("API прогнозу повернув некоректний JSON.") from error

        return data


class WeatherAdapter:

    def normalize(self, city_data, forecast_data):
        hourly = forecast_data.get("hourly")
        if not isinstance(hourly, dict):
            raise WeatherError("У відповіді немає коректного поля hourly.")

        times = hourly.get("time")
        temperatures = hourly.get("temperature_2m")
        probabilities = hourly.get("precipitation_probability")

        if not isinstance(times, list) or not isinstance(temperatures, list):
            raise WeatherError("У прогнозі відсутні масиви часу або температури.")
        if probabilities is not None and not isinstance(probabilities, list):
            raise WeatherError("Масив імовірності опадів має некоректний формат.")
        if probabilities is None:
            probabilities = [None] * len(times)

        if len(times) != len(temperatures) or len(times) != len(probabilities):
            raise WeatherError("Масиви прогнозу мають різну довжину.")

        hours = []
        for time_value, temperature, probability in zip(times, temperatures, probabilities):
            if not isinstance(time_value, str) or not isinstance(temperature, (int, float)):
                raise WeatherError("У прогнозі знайдено некоректний час або температуру.")
            if probability is not None and not isinstance(probability, (int, float)):
                raise WeatherError("Некоректне значення ймовірності опадів.")
            hours.append(
                HourForecast(
                    time=time_value,
                    temperature_c=float(temperature),
                    precipitation_probability=(
                        float(probability) if probability is not None else None
                    ),
                )
            )

        if not hours:
            raise WeatherError("Сервіс не повернув погодинних прогнозів.")

        try:
            latitude = float(city_data["latitude"])
            longitude = float(city_data["longitude"])
        except (KeyError, TypeError, ValueError) as error:
            raise WeatherError("Не вдалося прочитати координати міста.") from error

        return WeatherForecast(
            city=city_data["name"],
            latitude=latitude,
            longitude=longitude,
            retrieved_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            hours=hours,
        )


def ttl_cache(ttl_seconds=600):

    def decorator(function):
        cache = {}

        @wraps(function)
        def wrapper(self, latitude, longitude):
            key = (round(float(latitude), 4), round(float(longitude), 4))
            now = monotonic()

            if key in cache:
                expires_at, cached_value = cache[key]
                if now < expires_at:
                    self.last_cache_hit = True
                    return cached_value
                del cache[key]

            self.last_cache_hit = False
            result = function(self, latitude, longitude)
            cache[key] = (now + ttl_seconds, result)
            return result

        wrapper.cache = cache
        return wrapper

    return decorator


class CachedForecastProvider:

    def __init__(self, provider, ttl_seconds=600):
        self.provider = provider
        self.ttl_seconds = ttl_seconds
        self.last_cache_hit = False
        self._get_cached = self._make_cached_method()

    def _make_cached_method(self):
        @ttl_cache(self.ttl_seconds)
        def cached_call(instance, latitude, longitude):
            return instance.provider.get_forecast(latitude, longitude)

        # Декоратор зберігає сумісний інтерфейс (lat, lon).
        return cached_call.__get__(self, CachedForecastProvider)

    def get_forecast(self, latitude, longitude):
        return self._get_cached(latitude, longitude)

    @property
    def http_requests(self):
        return self.provider.http_requests


class WeatherFacade:

    def __init__(self, history=None, ttl_seconds=600):
        self.geocoder = GeocodingClient()
        self.forecast_provider = ForecastProvider()
        self.cached_provider = CachedForecastProvider(
            self.forecast_provider, ttl_seconds=ttl_seconds
        )
        self.adapter = WeatherAdapter()
        self.history = history
        self.last_cache_hit = False

    @property
    def forecast_provider_http_requests(self):
        return self.forecast_provider.http_requests

    @property
    def http_requests(self):
        return self.forecast_provider.http_requests

    def get_weather(self, city_name):
        city_data = self.geocoder.find_city(city_name)
        raw_forecast = self.cached_provider.get_forecast(
            city_data["latitude"], city_data["longitude"]
        )
        self.last_cache_hit = self.cached_provider.last_cache_hit
        forecast = self.adapter.normalize(city_data, raw_forecast)

        if self.history is not None:
            self.history.save(forecast)

        return forecast
