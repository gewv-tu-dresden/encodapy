# Thermal Storage

This is a component for calculating the thermal storage capacity of a cylindrical upright tank, which is required for different steering concepts.
## Functionality

The component uses measurement values from temperature sensors to calculate the thermal energy and state of charge of a thermal storage tank. To achieve this, three to ten temperature sensors in the storage could be used.

### Outputs
- Storage charge in percent (0–100): `storage__level`
- Storage energy content in Wh: `storage__energy`
- Additional storable energy in Wh: `storage__loading_potential_nominal`

A overview is avaiable als Pydantic BaseModel `ThermalStorageOutputData` in [thermal_storage_config.py](./thermal_storage_config.py).

### Calculation Methods
Two calculation methods are available, selected via the component configuration:
- **Static Limits**: Defined in the sensor configuration (`static_limits`)
- **Connection Limits**: Uses temperature sensors from the in- and outflow as limits (`connection_limits`)
- **Historical Limits**: At startup, it uses the externally defined sensor configuration (`historical_limits`). It then calibrates the limits based on historical data.
  - Refer to the `ThermalStorageCalibrationConfig` section in the component's configuration.
  - It stores the calibration results in an SQLite database. For the path, see the ThermalStorageCalibrationConfig for persistent data storage.

The default method is **Static Limits**.

## Component Configuration

The service requires a specific configuration defined by a Pydantic `BaseModel`, which includes:
- **Temperature Sensors Configuration** (`ThermalStorageTemperatureSensors`):
  - Between three and ten sensors can be used.
  - For each sensor, specify the name, height in the tank (as a percentage from the top down, 0–100%), and limits.
  - Sensor 1 should be the highest.
- **Storage Tank Volume**: Assumes a cylindrical upright storage tank.
- **Medium in the Storage Tank**
- **Calculation Method** (see above)
- **Load Level Check**: Compare the storage energy level with the temperature of the upper sensor to see if it is within the limits.
- **Calibration**: For more information about the calibration, see the `ThermalStorageCalibrationConfig`.

Configuration parameters must be set as datapoints or connections to static data in the config file. For more details, see the `ThermalStorageConfigData` in [thermal_storage_config.py](./thermal_storage_config.py) or the documentation.

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

For detailed documentation of the inputs, see the `ThermalStorageInputData` in [thermal_storage_config.py](./thermal_storage_config.py) or the documentation.

## Example
A example how the component could be used is avaiable in [examples/06_thermal_storage_service](./../../../examples/06_thermal_storage_service/)