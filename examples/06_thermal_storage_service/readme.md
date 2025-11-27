# Component Thermal Storage

## Overview

Example of the use of the thermal storage component in EnCoDaPy. The example uses a connection to a FIWARE platform. The following parts show different aspects of the application:

- [configure_fiware_platform.ipynb](./configure_fiware_platform.ipynb): Notebook to add the needed configuration and values to the fiware platform
- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [thermal_storage_service.py](./thermal_storage_service.py): Code of the service for the thermal storage
- [main.py](./main.py): Script to start the service
- [run_thermal_storage_service.ipynb](./run_thermal_storage_service.ipynb): Notebook to run the service (you can also run [encodapy.service.service_main](./../../encodapy/service/service_main.py))

## Usage

To run the example, you need to add a [.env](.env):

```
FIWARE_IOTA= ["http://localhost:4041"]      # URL of the IoT Agent
FIWARE_CB= ["http://localhost:1026"]        # URL of the Context Broker
FIWARE_SERVICE= ["thermal_storage_service"] # Name of the FIWARE Service
FIWARE_SERVICE_PATH= ["/"]                  # FIWARE Service Path, usually "/"
LOG_LEVEL=["WARNING"]                       # Level for Logging Messages ("DEBUG" to get more information)

RELOAD_STATICDATA=False                     # Should the static data be reloaded?
```

Furthermore, a running FIWARE platform ([n5geh.platform](https://github.com/N5GEH/n5geh.platform) - "NGSI-v2" version) is required to which a connection can be established with the above specified data. The configuration of the data points in the platform can be created with the following notebook [run_thermal_storage_service.ipynb](./run_thermal_storage_service.ipynb).
For a local usage of the FIWARE platform, you can use the following docker-compose.yml: <https://github.com/N5GEH/n5geh.platform/blob/master/v2/docker-compose.yml>

See the documentation under [encodapy/components/thermal_storage](./../../encodapy/components/thermal_storage/readme.md) for more details.
