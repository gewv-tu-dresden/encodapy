# Weather Data

This is a component to get current and forecast weather data from Brightsky. 

## Functionality

The component uses coordination values to get located weather data from Brightsky. https://brightsky.dev/ 
Bright Sky is a free and open-source weather API. It aims to provide an easy-to-use gateway to weather data that the DWD – Germany's meteorological service – publishes on their open data server.

The public instance at https://api.brightsky.dev/ is free-to-use for all purposes, no API key required! Please note that the DWD's Terms of Use (https://www.dwd.de/EN/service/legal_notice/legal_notice.html) apply to all data you retrieve through the API.

implemented Data:

- current weather
- forecast weather

## Description
Depending on the selected outputs (current/forecast), the respective requests are executed and the corresponding values ​​are output.

### Inputs
No inputs are requiered

### Static Data

coordinates of the building:
- longitude 
- latitude
time settings:
Forecast period:
- forecast_time_range [optional] (default value: 1d)
Time interval for retrieving current weather data: (independent of the sampling_time in the config)
- time_interval_current_weather [optional] (default value 15M)
Time interval for retrieving forecast weather data: (independent of the sampling_time in the config)
- time_interval_forecast_weather [optional] (default value 3h)


### Outputs
all implemented outputs are optional

- "temperature": outside temperature in °C
- "relative_humidity": relative humidity in % 
- "dew_point": dew point of air in °C 
- "pressure_msl": Atmospheric pressure at timestamp, reduced to mean sea level hPa
- "solar_60": Sunshine duration during previous 60 minutes in kWh / m²
- "forecast_temperature" : dict of outside temperature in °C
- "forecast_solar" : dict of solar_60 kWh / m²
