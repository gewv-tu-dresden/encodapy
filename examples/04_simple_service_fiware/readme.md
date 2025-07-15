# Example for usage with a simple service
## Overview
As an example of a simple service using EnCoDaPy, a heating regulator based on a two-position regulator is created. The example shows a connection to a FIWARE platform. The following parts show different aspects of the application:
- [configure_fiware_platform.ipynb](./configure_fiware_platform.ipynb): Notebook to add the needed configuration and values to the fiware platform
- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [example_service.py](./example_service.py): Code of the service example
- [main.py](./main.py): Script to start the service
- [run_simple_service.ipynb](./run_simple_service.ipynb): Notebook to run the service (also possible to run the [main.py](./main.py))

To run the example, you need to add a [.env](.env):
```
FIWARE_IOTA= ["http://localhost:4041"]      # URL of the IoT Agent
FIWARE_CB= ["http://localhost:1026"]        # URL of the Context Broker
FIWARE_SERVICE= ["example_service"]         # Name of the FIWARE Service
FIWARE_SERVICE_PATH= ["/"]                  # FIWARE Service Path, usually "/"
LOG_LEVEL=["WARNING]                        # Level for Logging Messages ("DEBUG" to get more information)
```
Furthermore, a running FIWARE platform ([n5geh.platform](https://github.com/N5GEH/n5geh.platform) - "NGSI-v2" version) is required to which a connection can be established with the above specified data. The configuration of the data points in the platform can be created with the following notebook [run_simple_service.ipynb](./run_simple_service.ipynb).

## Basics
To create your own custom service, you have to overwrite three functions of the [ControllerBasicService](./../../encodapy/service/basic_service.py):
- `prepare_start`: This is a synchronous function that prepares the start of the algorithm and specifies aspects of the service. This should not take long due to health issues in Docker containers. It only needs to be overwritten if other tasks are required after initialisation of the service.
- `calculation`: Asynchronous function to perform the main calculation in the service
- `calibration`: Asynchrone function to calibrate the service or coefficients in the service if required

For the models of the inputs and outputs see [02_datatransfer](./../02_datatransfer/)