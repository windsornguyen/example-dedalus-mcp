# Copyright (c) 2025 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Open-Meteo weather API operations for MCP server.

Provides weather forecasts, historical data, air quality, marine conditions,
flood forecasts, and geocoding via Open-Meteo's free APIs.

No authentication required - all endpoints are public.
"""

from typing import Any

from dedalus_mcp import HttpMethod, HttpRequest, get_context, tool
from dedalus_mcp.auth import Connection
from pydantic import BaseModel


# --- Connections (one per API host) ------------------------------------------

forecast_api = Connection(
    name="open_meteo_forecast",
    credentials=None,
    base_url="https://api.open-meteo.com",
)

archive_api = Connection(
    name="open_meteo_archive",
    credentials=None,
    base_url="https://archive-api.open-meteo.com",
)

air_quality_api = Connection(
    name="open_meteo_air_quality",
    credentials=None,
    base_url="https://air-quality-api.open-meteo.com",
)

marine_api = Connection(
    name="open_meteo_marine",
    credentials=None,
    base_url="https://marine-api.open-meteo.com",
)

flood_api = Connection(
    name="open_meteo_flood",
    credentials=None,
    base_url="https://flood-api.open-meteo.com",
)

seasonal_api = Connection(
    name="open_meteo_seasonal",
    credentials=None,
    base_url="https://seasonal-api.open-meteo.com",
)

ensemble_api = Connection(
    name="open_meteo_ensemble",
    credentials=None,
    base_url="https://ensemble-api.open-meteo.com",
)

geocoding_api = Connection(
    name="open_meteo_geocoding",
    credentials=None,
    base_url="https://geocoding-api.open-meteo.com",
)

weather_connections = [
    forecast_api,
    archive_api,
    air_quality_api,
    marine_api,
    flood_api,
    seasonal_api,
    ensemble_api,
    geocoding_api,
]


# --- Response Models ---------------------------------------------------------


class WeatherResult(BaseModel):
    """Generic weather API result."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class GeocodingResult(BaseModel):
    """Geocoding search result."""

    success: bool
    results: list[dict[str, Any]] | None = None
    error: str | None = None


# --- Helper ------------------------------------------------------------------


def _build_query(params: dict[str, Any]) -> str:
    """Build URL query string from params, handling lists."""
    parts = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, list):
            parts.append(f"{k}={','.join(str(x) for x in v)}")
        elif isinstance(v, bool):
            parts.append(f"{k}={str(v).lower()}")
        else:
            parts.append(f"{k}={v}")
    return "&".join(parts)


async def _weather_request(connection_name: str, path: str, params: dict[str, Any]) -> WeatherResult:
    """Make a weather API request."""
    ctx = get_context()
    query = _build_query(params)
    full_path = f"{path}?{query}" if query else path
    request = HttpRequest(method=HttpMethod.GET, path=full_path)
    response = await ctx.dispatch(connection_name, request)

    if response.success:
        return WeatherResult(success=True, data=response.response.body)

    msg = response.error.message if response.error else "Request failed"
    return WeatherResult(success=False, error=msg)


# --- Weather Forecast Tools --------------------------------------------------


@tool(description="Get weather forecast for a location (1-16 days ahead)")
async def weather_forecast(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
    timezone: str = "auto",
    forecast_days: int = 7,
) -> WeatherResult:
    """Get weather forecast from Open-Meteo.

    Args:
        latitude: Location latitude (-90 to 90).
        longitude: Location longitude (-180 to 180).
        hourly: Hourly variables (e.g., ["temperature_2m", "precipitation"]).
        daily: Daily variables (e.g., ["temperature_2m_max", "sunrise"]).
        temperature_unit: celsius or fahrenheit.
        wind_speed_unit: kmh, ms, mph, or kn.
        precipitation_unit: mm or inch.
        timezone: Timezone name or "auto".
        forecast_days: Number of forecast days (1-16).

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "precipitation_unit": precipitation_unit,
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    return await _weather_request("open_meteo_forecast", "/v1/forecast", params)


@tool(description="Get historical weather data (ERA5 reanalysis, 1940-present)")
async def weather_archive(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get historical weather data from Open-Meteo archive.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        hourly: Hourly variables to retrieve.
        daily: Daily variables to retrieve.
        temperature_unit: celsius or fahrenheit.
        timezone: Timezone name or "auto".

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_archive", "/v1/archive", params)


@tool(description="Get elevation for coordinates using digital elevation model")
async def weather_elevation(latitude: float, longitude: float) -> WeatherResult:
    """Get elevation data for a location.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.

    """
    params = {"latitude": latitude, "longitude": longitude}
    return await _weather_request("open_meteo_forecast", "/v1/elevation", params)


# --- Air Quality Tool --------------------------------------------------------


@tool(description="Get air quality forecast (PM2.5, PM10, ozone, NO2, etc.)")
async def air_quality(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    timezone: str = "auto",
    past_days: int = 0,
    forecast_days: int = 5,
) -> WeatherResult:
    """Get air quality forecast from Open-Meteo.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        hourly: Pollutant variables (e.g., ["pm2_5", "pm10", "ozone", "nitrogen_dioxide"]).
        timezone: Timezone name or "auto".
        past_days: Include past days (0-7).
        forecast_days: Number of forecast days.

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly or ["pm2_5", "pm10", "ozone", "nitrogen_dioxide"],
        "timezone": timezone,
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    return await _weather_request("open_meteo_air_quality", "/v1/air-quality", params)


# --- Marine Weather Tool -----------------------------------------------------


@tool(description="Get marine weather forecast (waves, sea temperature)")
async def marine_weather(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    timezone: str = "auto",
    forecast_days: int = 7,
) -> WeatherResult:
    """Get marine weather forecast from Open-Meteo.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        hourly: Hourly marine variables (e.g., ["wave_height", "wave_period"]).
        daily: Daily marine variables.
        timezone: Timezone name or "auto".
        forecast_days: Number of forecast days.

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly or ["wave_height", "wave_period", "wave_direction"],
        "daily": daily,
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    return await _weather_request("open_meteo_marine", "/v1/marine", params)


# --- Flood Forecast Tool -----------------------------------------------------


@tool(description="Get river discharge and flood forecasts (GloFAS)")
async def flood_forecast(
    latitude: float,
    longitude: float,
    daily: list[str] | None = None,
    timezone: str = "auto",
    forecast_days: int = 92,
) -> WeatherResult:
    """Get flood forecast from Open-Meteo (GloFAS data).

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        daily: Daily variables (e.g., ["river_discharge"]).
        timezone: Timezone name or "auto".
        forecast_days: Number of forecast days (up to 210).

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": daily or ["river_discharge"],
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    return await _weather_request("open_meteo_flood", "/v1/flood", params)


# --- Seasonal Forecast Tool --------------------------------------------------


@tool(description="Get long-range seasonal forecast (up to 9 months)")
async def seasonal_forecast(
    latitude: float,
    longitude: float,
    sixhourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
    forecast_days: int = 92,
) -> WeatherResult:
    """Get seasonal forecast from Open-Meteo.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        sixhourly: 6-hourly variables.
        daily: Daily variables (e.g., ["temperature_2m_max", "precipitation_sum"]).
        temperature_unit: celsius or fahrenheit.
        timezone: Timezone name or "auto".
        forecast_days: Number of forecast days (45, 92, 183, or 274).

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "sixhourly": sixhourly,
        "daily": daily or ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "temperature_unit": temperature_unit,
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    return await _weather_request("open_meteo_seasonal", "/v1/seasonal", params)


# --- Climate Projection Tool -------------------------------------------------


@tool(description="Get climate change projections (CMIP6 models)")
async def climate_projection(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    models: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
) -> WeatherResult:
    """Get climate projections from CMIP6 models.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        models: Climate models to use.
        daily: Daily variables to retrieve.
        temperature_unit: celsius or fahrenheit.

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "models": models,
        "daily": daily or ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "temperature_unit": temperature_unit,
    }
    return await _weather_request("open_meteo_forecast", "/v1/climate", params)


# --- Ensemble Forecast Tool --------------------------------------------------


@tool(description="Get ensemble forecast with uncertainty quantification")
async def ensemble_forecast(
    latitude: float,
    longitude: float,
    models: list[str] | None = None,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
    forecast_days: int = 7,
) -> WeatherResult:
    """Get ensemble forecast showing prediction uncertainty.

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        models: Ensemble models to use.
        hourly: Hourly variables.
        daily: Daily variables.
        temperature_unit: celsius or fahrenheit.
        timezone: Timezone name or "auto".
        forecast_days: Number of forecast days (1-35).

    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "models": models,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
        "forecast_days": forecast_days,
    }
    return await _weather_request("open_meteo_ensemble", "/v1/ensemble", params)


# --- Regional Weather Model Tools --------------------------------------------


@tool(description="Get forecast from DWD ICON model (Germany/Europe)")
async def weather_dwd_icon(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from DWD ICON model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/dwd-icon", params)


@tool(description="Get forecast from GFS model (USA/Global)")
async def weather_gfs(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from NOAA GFS model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/gfs", params)


@tool(description="Get forecast from Meteo-France model (France/Europe)")
async def weather_meteofrance(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from Meteo-France model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/meteofrance", params)


@tool(description="Get forecast from ECMWF model (European/Global)")
async def weather_ecmwf(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from ECMWF model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/ecmwf", params)


@tool(description="Get forecast from JMA model (Japan/Asia)")
async def weather_jma(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from JMA model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/jma", params)


@tool(description="Get forecast from MetNo model (Norway/Nordic)")
async def weather_metno(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from Norwegian Met model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/metno", params)


@tool(description="Get forecast from GEM model (Canada/North America)")
async def weather_gem(
    latitude: float,
    longitude: float,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    temperature_unit: str = "celsius",
    timezone: str = "auto",
) -> WeatherResult:
    """Get forecast from Canadian GEM model."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly,
        "daily": daily,
        "temperature_unit": temperature_unit,
        "timezone": timezone,
    }
    return await _weather_request("open_meteo_forecast", "/v1/gem", params)


# --- Geocoding Tool ----------------------------------------------------------


@tool(description="Search for locations by name or postal code")
async def geocoding(
    name: str,
    count: int = 10,
    language: str = "en",
    country_code: str | None = None,
) -> GeocodingResult:
    """Search for locations using Open-Meteo geocoding.

    Args:
        name: Location name or postal code (min 2 characters).
        count: Number of results (1-100).
        language: Language code for results (e.g., "en", "de", "fr").
        country_code: ISO country code to filter results.

    """
    ctx = get_context()
    params: dict[str, Any] = {
        "name": name,
        "count": count,
        "language": language,
        "format": "json",
    }
    if country_code:
        params["countryCode"] = country_code

    query = _build_query(params)
    request = HttpRequest(method=HttpMethod.GET, path=f"/v1/search?{query}")
    response = await ctx.dispatch("open_meteo_geocoding", request)

    if response.success:
        body = response.response.body
        results = body.get("results", []) if isinstance(body, dict) else []
        return GeocodingResult(success=True, results=results)

    msg = response.error.message if response.error else "Geocoding failed"
    return GeocodingResult(success=False, error=msg)


# --- Export ------------------------------------------------------------------

weather_tools = [
    # Core weather
    weather_forecast,
    weather_archive,
    weather_elevation,
    # Specialized forecasts
    air_quality,
    marine_weather,
    flood_forecast,
    seasonal_forecast,
    climate_projection,
    ensemble_forecast,
    # Regional models
    weather_dwd_icon,
    weather_gfs,
    weather_meteofrance,
    weather_ecmwf,
    weather_jma,
    weather_metno,
    weather_gem,
    # Geocoding
    geocoding,
]
