# Example for usage with a simple mqtt service

## Overview

As an example of a simple service using Encodapy with a MQTT interface, a heating controller based on a two-position regulator is created. The example is more or less the same as in [04_simple_service_fiware](./../04_simple_service_fiware/), but shows a connection to a MQTT broker. The following parts show different aspects of the application:

- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [mqtt_controller.py](./mqtt_controller.py): Code of the service example
- [main.py](./main.py): Script to start the service

To run the example, you could optionally add a `.env` file with the following content (if you do not add your own, the here written standard values will be used):

```env
MQTT_BROKER="localhost"  # URL of the MQTT Broker
MQTT_PORT=1883           # Port of the MQTT Broker
MQTT_USERNAME=""         # if required
MQTT_PASSWORD=""         # if required
MQTT_TOPIC_PREFIX=""     # optional, used as prefix for all topics 
LOG_LEVEL="WARNING"      # Level for Logging Messages ("DEBUG" to get more information)
```

Furthermore, a running MQTT broker is required to which a connection can be established with the above-specified data.

## Basics

To create your own custom service, you have to overwrite two functions of the [ControllerBasicService](./../../encodapy/service/basic_service.py):
- `prepare_start`: This is a synchronous function that prepares the start of the algorithm and specifies aspects of the service. This should not take long due to health issues in Docker containers. It only needs to be overwritten if other tasks are required after initialisation of the service.
- `calculation`: Asynchronous function to perform the main calculation in the service
- `calibration`: Asynchronous function to calibrate the service or coefficients in the service if required

For the models of the inputs and outputs, see [02_datatransfer](./../02_datatransfer/).
