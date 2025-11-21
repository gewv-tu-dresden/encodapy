# Component Runner

## Overview

This example demonstrates how to use the component runner from EnCoDaPy. It provides a standardized way to utilize components (`encodapy.components`). You only need to add the components in the config and connect them via their inputs and outputs. The output from one component can be used as input for another.

The example uses a connection to a FIWARE platform, which is needed (see [n5geh.platform](https://github.com/N5GEH/n5geh.platform) - "NGSI-v2" version). The following parts show different aspects of the example:

- [configure_fiware_platform.ipynb](./configure_fiware_platform.ipynb): Notebook to add the needed configuration and values to the fiware platform
- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [run_components.ipynb](./run_components.ipynb): Notebook to run the service (also possible to run the [encodapy.service.service_main](./../../encodapy/service/service_main.py) with the necessary envs)
- [main.py](./main.py): Main function to run the service

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

## Functionality

This example shows how two components could work together.

- The "Thermal Storage" component is used to calculate the load level of the thermal storage tank.
- The "Two Point Controller" component is used to calculate a steering signal for loading the storage tank.

If the environment variable `RELOAD_STATICDATA` is set to True, the `calibration()` function will adjust the static configuration data in each calibration cycle.

For the function of the component "Thermal Storage" see [06_thermal_storage_service](./../06_thermal_storage_service/).

If you would like to use it with other components, you could either use an existing component from EnCoDaPy or add a new one. For more information, see [encodapy/components](./../../encodapy/components).
