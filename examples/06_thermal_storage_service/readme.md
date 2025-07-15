# Component Thermal Storage

## Overview
Example of the use of the thermal storage component in EnCoDaPy. The example uses a connection to a FIWARE platform. The following parts show different aspects of the application:
- [configure_fiware_platform.ipynb](./configure_fiware_platform.ipynb): Notebook to add the needed configuration and values to the fiware platform
- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [thermal_storage_service.py](./example_service.py): Code of the service for the thermal storage
- [main.py](./main.py): Script to start the service
- [run_simple_service.ipynb](./run_simple_service.ipynb): Notebook to run the service (also possible to run the [main.py](./main.py))

## Usage
To run the example, you need to add a [.env](.env):
```
FIWARE_IOTA= ["http://localhost:4041"]      # URL of the IoT Agent
FIWARE_CB= ["http://localhost:1026"]        # URL of the Context Broker
FIWARE_SERVICE= ["thermal_storage_service"] # Name of the FIWARE Service
FIWARE_SERVICE_PATH= ["/"]                  # FIWARE Service Path, usually "/"
LOG_LEVEL=["WARNING]                        # Level for Logging Messages ("DEBUG" to get more information)
```
Furthermore, a running FIWARE platform ([n5geh.platform](https://github.com/N5GEH/n5geh.platform) - "NGSI-v2" version) is required to which a connection can be established with the above specified data. The configuration of the data points in the platform can be created with the following notebook [run_simple_service.ipynb](./run_simple_service.ipynb).

## Functionality

The service uses measurement values from temperature sensors to calculate the thermal energy and state of charge of a thermal storage tank. To achieve this, three to five temperature sensors could be used.

The service requires a specific configuration defined by a Pydantic base model and contains:
- The configuration of the temperature sensors `ThermalStorageTemperatureSensors`:
    - Between three and five sensors could be used.
    - For each sensor the name, the height in the tank and the limits needs to be set.
    - The height of each sensor should be expressed as a percentage (0–100%) from the top down. Sensor 1 should be the highest.
- The information about the volume of the storage tank
    - The assumption is made that a cylindrical upright storage tank is used.
- The medium in the storage tank

The following temperature sensors are required (optional) as inputs, which are used in the configuration of the sensors:
- `temperature_1`
- `temperature_2`
- `temperature_3`
- `temperature_4` (optional)
- `temperature_5` (optional)

The outputs are:
- The storage charge in percent (0 - 100): `storage__level`
- The storage energy content in Wh: `storage__energy`