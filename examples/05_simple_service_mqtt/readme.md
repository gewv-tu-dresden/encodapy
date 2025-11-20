# Example for usage with a simple mqtt service

## Overview

As an example of a simple service using Encodapy with a MQTT interface, a heating controller based on a two-position regulator is created. The example is more or less the same as in [04_simple_service_fiware](./../04_simple_service_fiware/), but shows a connection to a MQTT broker. The following parts show different aspects of the application:

- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [mqtt_controller.py](./mqtt_controller.py): Code of the service example
- [main.py](./main.py): Script to start the service
- [storage_dummy.py](./storage_dummy.py): Script to send different types of mqtt messages from a dummy storage to the service

To run the example, you *need to add* a `.env` file with the content for MQTT_TEMPLATE_EXAMPLE03 (if you do not add the others, the here written standard values will be used):

```env
MQTT_TEMPLATE_EXAMPLE03 = "custom_mqtt_template.json" # the only mandatory information

MQTT_HOST="localhost"    # URL of the MQTT Broker
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

For the possible payloads, see [03_interfaces](./../03_interfaces/).

The example uses the possibilites of the optional "Data Transfer Formats" for Outputs, see [03_interfaces - Outputs](./../03_interfaces/readme.md#outputs).

- In the config, you can switch the mqtt_format of the output attributes from "boiler-controller".
- You can build your very own format in [custom_mqtt_template.json](./custom_mqtt_template.json).

## Usage

- To use it, the `.env` file must be created and an MQTT broker with the data in the `.env` file must be available so that a connection can be established.
- The service is started by executing [`main.py`](./main.py) from the current path.
- New data can be sent by running the script [`storage_dummy.py`](./storage_dummy.py).
- Look at the DEBUG messages or use [MQTT Explorer](https://mqtt-explorer.com) to see the different kinds of possible mqtt messages.
