# Thermal Storage

This is a component for calculating the thermal storage capacity of a cylindrical upright tank, which is required for different steering concepts.

## Functionality

The component uses measurement values from temperature sensors to calculate the thermal energy and state of charge of a thermal storage tank. To achieve this, three to ten temperature sensors in the storage could be used.

### Outputs

- Storage charge in percent (0–100): `storage__level`
- Storage energy content in Wh: `storage__energy`
- Additional storable energy in Wh: `storage__loading_potential_nominal`

An overview is available as Pydantic BaseModel {py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageOutputData` in [thermal_storage_config.py](./thermal_storage_config.py).

If the Temperature Check (`load_level_check` in {py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageConfigData`) is enabled, the temperature of the sensor is checked and if the levels fall below the limits, the charge level is adjusted. See [Component Configuration](#component-configuration) for the information on adding this to temperature sensors.

### Calculation Methods

Two calculation methods are available, selected via the component configuration:

- **Static Limits**: Defined in the sensor configuration (`static_limits`)
- **Connection Limits**: Uses temperature sensors from the in- and outflow as limits (`connection_limits`)
- **Historical Limits**: At startup, it uses the externally defined sensor configuration (`historical_limits`). It then calibrates the limits based on historical data.
  - Refer to the {py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageCalibrationConfig` section in the component's configuration.
  - It stores the calibration results in an SQLite database. For the path, see the ThermalStorageCalibrationConfig for persistent data storage.

The default method is **Static Limits**.

### Calibration (Historical Limits)

If `historical_limits` is used as calculation method, the component calibrates the
sensor limits using stored historical temperatures per sensor.

- At startup, stored limits are loaded from the calibration database (if available).
- During operation, new temperature extrema are collected from historical sensor values.
- New limits are calculated from configured limits and historical extrema with a margin.
- Protected limits (`protected_lower_limit`, `protected_upper_limit`) are not changed.
- Updated extrema and calibrated limits are persisted in SQLite.

For each non-protected sensor, the calibrated limits are calculated as:

- Lower limit: average of configured lower limit and historical minimum reduced by margin
- Upper limit: average of configured upper limit and historical maximum increased by margin

## Component Configuration

The service requires a specific configuration defined by a Pydantic `BaseModel`, which includes:

- **Temperature Sensors Configuration** ({py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageTemperatureSensors`):
  - Between three and ten sensors can be used.
  - For each sensor, specify the name, height in the tank (as a percentage from the top down, 0–100%), and limits.
  - Sensor 1 should be the highest.
  - You can specify whether the limits should be checked (`temperature_check`) and whether they should not be adjusted during calibration (`protected_upper_limit` / `protected_lower_limit`)
  - See {py:class}`~encodapy.components.thermal_storage.thermal_storage_config.StorageSensorConfig` for more details
- **Storage Tank Volume**: Assumes a cylindrical upright storage tank.
- **Medium in the Storage Tank**
- **Calculation Method** (see above)
- **Load Level Check**: Compare the storage energy level with the temperature of the upper sensor to see if it is within the limits.
- **Calibration** ({py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageCalibrationConfig`): Required for `historical_limits`.
  - `historical_data_margin` (0-100%): Safety margin applied to historical extrema before calculating new limits.
  - `historical_timerange_minimum` (hours): Minimum historical timespan needed before new extrema are used.
  - `historical_timerange_retention` (hours): Retention period for in-memory historical data.
  - `db_path` (optional): This is the SQLite storage path for calibrated limits and extremes. If it is set to 'None', no data will be stored persistently.

To enable calibration, configure:

- `calculation_method = historical_limits`
- `calibration` with suitable values for margin and timeranges
- Optional sensor protection flags in each storage sensor:
  - `protected_lower_limit`
  - `protected_upper_limit`
  - `temperature_check` (automatically enforces lower-limit protection)
- Calibration must be enabled in the general configuration (sample time).

Configuration parameters must be set as datapoints or connections to static data in the config file. For more details, see the {py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageConfigData` in [thermal_storage_config.py](./thermal_storage_config.py) or the documentation.

## Inputs

The following temperature sensors are required (optional) as inputs, as defined in the sensor configuration:

- `temperature_1`
- `temperature_2`
- `temperature_3`
- `temperature_4` (optional)
- `temperature_5` (optional)
- `temperature_6` (optional)
- `temperature_7` (optional)
- `temperature_8` (optional)
- `temperature_9` (optional)
- `temperature_10` (optional)

If you want to use load connection sensors as references for the limits, provide the following inputs (`connection_limits`):

- `load_temperature_in`
- `load_temperature_out`

For detailed documentation of the inputs, see the {py:class}`~encodapy.components.thermal_storage.thermal_storage_config.ThermalStorageInputData` in [thermal_storage_config.py](./thermal_storage_config.py) or the documentation.

## Example

An example how the component could be used is available in [examples/06_thermal_storage_service](./../../../examples/06_thermal_storage_service/)