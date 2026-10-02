# Weather Data

This is a component to get current and forecast weather data from [Brightsky](https://brightsky.dev/).

## Functionality

The component uses coordinates to get located weather data from [Brightsky](https://brightsky.dev/).
Bright Sky is a free and open-source weather API. It aims to provide an easy-to-use gateway to weather data that the DWD – Germany's meteorological service – publishes on their open data server.

The public instance at [api.brightsky.dev](https://api.brightsky.dev/) is free-to-use for all purposes, no API key required! Please note that the [DWD's Terms of Use](https://www.dwd.de/EN/service/legal_notice/legal_notice.html) apply to all data you retrieve through the API.

Implemented data:

- current weather
- forecast weather

Depending on the selected outputs, the component determines which API calls (current and/or forecast) are necessary, executes the respective requests, and outputs the corresponding values. At least one output must be configured, otherwise the component raises an error during preparation.

The retrieval of the weather data is controlled by its own time intervals (see [Component Configuration](#component-configuration)), independent of the `sampling_time` in the service config. Until the next interval is reached, the data of the last API call is used.

## Component Configuration

The configuration model is {py:class}`~encodapy.components.weather_data.weather_data_config.WeatherDataConfigData` in [weather_data_config.py](./weather_data_config.py).

Coordinates of the location:

- `longitude`: longitude of the chosen location in degree (default value: 13.4, Berlin)
- `latitude`: latitude of the chosen location in degree (default value: 52.5, Berlin)

Time settings:

- `forecast_time_range` (optional): forecast time range to retrieve (default value: 1 day)
- `time_interval_current_weather` (optional): time interval for retrieving current weather data, independent of the `sampling_time` in the config (default value: 15 minutes)
- `time_interval_forecast_weather` (optional): time interval for retrieving forecast weather data, independent of the `sampling_time` in the config (default value: 3 hours)

Configuration parameters must be set as datapoints or connections to static data in the config file.

### Minimal Configuration Example

This component block illustrates the relevant part of a service configuration:

```json
{
  "id": "weatherdata",
  "type": "weather_data",
  "inputs": {},
  "outputs": {
    "temperature": {
      "entity": "weatherdata",
      "attribute": "temperature"
    },
    "forecast_temperature": {
      "entity": "weatherdata",
      "attribute": "forecast_temperature"
    }
  },
  "config": {
    "longitude": {
      "entity": "weatherdata",
      "attribute": "longitude"
    },
    "latitude": {
      "entity": "weatherdata",
      "attribute": "latitude"
    },
    "forecast_time_range": {
      "entity": "weatherdata",
      "attribute": "forecast_time_range"
    },
    "time_interval_current_weather": {
      "entity": "weatherdata",
      "attribute": "time_interval_current_weather"
    },
    "time_interval_forecast_weather": {
      "entity": "weatherdata",
      "attribute": "time_interval_forecast_weather"
    }
  }
}
```

For a full working configuration, see the [example](#example).

## Inputs

No inputs are required. The input model is {py:class}`~encodapy.components.weather_data.weather_data_config.WeatherDataInputData`.

## Outputs

All implemented outputs are optional, but at least one output must be configured. The output model is {py:class}`~encodapy.components.weather_data.weather_data_config.WeatherDataOutputData` in [weather_data_config.py](./weather_data_config.py).

Current weather:

- `temperature`: air temperature at timestamp, 2 m above the ground in °C
- `relative_humidity`: relative humidity at timestamp in %
- `dew_point`: dew point at timestamp, 2 m above ground in °C
- `pressure_msl`: atmospheric pressure at timestamp, reduced to mean sea level in Pa
- `solar_60`: solar irradiation during the previous 60 minutes in J / m²

Forecast weather:

- `forecast_temperature`: dict of forecast outside temperature in °C
- `forecast_solar`: dict of forecast solar irradiation during the previous 60 minutes in J / m²

The forecast outputs are dicts with the timestamp of each forecast step as key (string) and the forecast value as value. The covered period is defined by `forecast_time_range`. The keys are ISO-8601 timestamps (including the UTC offset of the retrieval timezone, see [Timezone](#timezone)) and follow the hourly grid of the Brightsky weather endpoint. Since every key contains the full UTC offset, the timestamps can be converted to any other timezone downstream.

## Timezone

The timezone for the API retrieval is defined by the constant `WEATHER_DATA_TZ_NAME` in [weather_data_config.py](./weather_data_config.py) (default: `Europe/Berlin`). It is used for the component clock (interval checks) and passed to Brightsky as the `tz` parameter, so the API returns timestamps with the matching UTC offset. All output timestamps are therefore complete datetime information: the `time` field of the current weather datapoints is given in UTC, the forecast keys carry the offset of the retrieval timezone. Both can be converted to any other timezone by the receiving component.

## Error Handling

The component follows a "last known data" strategy: if an API request to Brightsky fails, the error is logged and the component keeps the last known output data. A failed request does not interrupt the calculation and no error code or error state is propagated to the framework or to connected components; the error is only visible in the log.

The following error cases are handled the same way, for current and forecast calls:

- HTTP status codes other than 200 (client and server errors)
- a response body that is no valid JSON (e.g. an HTML error page of a gateway)
- timeouts and connection/request errors
- incomplete or invalid weather data that fails the validation of the output model

The retry time step of an interval is only advanced after a successful API call. A failed call is therefore retried at the next calculation step (the next `sampling_time` of the service), not after the full configured interval. Until the first successful call, the outputs stay `None`.

## Example

A full working example is available in:

- [examples/10_brightsky_weather_service](./../../../examples/10_brightsky_weather_service/)

Relevant files:

- Example service configuration: [examples/10_brightsky_weather_service/config.json](./../../../examples/10_brightsky_weather_service/config.json)
- Example static data: [examples/10_brightsky_weather_service/static_data.json](./../../../examples/10_brightsky_weather_service/static_data.json)
- Notebook to run the example: [examples/10_brightsky_weather_service/run_weatherdata_service.ipynb](./../../../examples/10_brightsky_weather_service/run_weatherdata_service.ipynb)
