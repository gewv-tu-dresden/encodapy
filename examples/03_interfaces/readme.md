# Interfaces for data exchange

It is possible use different interfaces for the data exchange:

- FIWARE-API
- MQTT
- File

There are different kinds of datapoints, which are possible (see `encodapy.config.models`):

- Input-Data (see `InputModel`):
  - Data could be stored as attributes (`attributes`)
  - Type of the datapoint could be single-input data (`value`) and time series (`timeseries`)
- Outut-Data (see `OutputModel`):
  - Data could be:
    - a attribute (`AttributeModel`): Normal output, or something like a sensor value.
    - a command (`CommandModel`): Setpoints that should be transferred via the FIWARE platform.

## FIWARE-API

Data exchange with the data platform of the N5GEH / FIWARE platform using the following APIs

- Contextbroker Orion
  - retrieve the existing entities and attributes as well as the current data of each entity
  - return the output (attributes / commands)
- Time Series Database CrateDB
  - query time series
  - use more stable than FIWARE-GE Quantumleap

- The base service uses the [FiLiP](https://github.com/RWTH-EBC/FiLiP/tree/master/examples) Python library and standard FIWARE APIs. It is possible to connect to platforms with or without authentication, you need to adjust the environment variables.

---

## MQTT

### Inputs / Subscriptions

#### Topics

MQTT topics in EnCoDaPy are dynamically constructed for each input entity using:

- A topic prefix from the .env (e.g., `project/mysuperproject/`)
- The entity ID(_interface) (`entity.id_interface`)
- The attribute ID(_interface) (`attribute.id_interface`)

**Example topic:**

```
project/mysuperproject/thermal_storage/t_sen_bot
```

#### Message Store Structure

For each topic, the internal message store (`self.mqtt_message_store`) maintains:

- `entity_id`: The ID of the entity
- `attribute_id`: The ID of the attribute (optional)
- `payload`: The current value (e.g. measurement, status, a dict)
- `timestamp`: The time of the last update

If the service tries to `get_data` from an mqtt-attribute, it retrieves the latest value for the attribute from the internal MQTT message store (self.mqtt_message_store), extracts and converts the payload using the configured logic, and returns the result as part of the InputDataModel. If no value is available, the attribute is marked as unavailable.

#### Payloads

Payloads received via MQTT can have various formats:

- **Primitive values:** `int`, `float`, `str`, `bool` (e.g., `"22.5"`, `"on"`, `0`)
- **JSON objects:** Dictionaries or lists, e.g., `{"value": 42, "unit": "°C"}`
- **DataFrames:** Serialized as JSON strings
- **Empty messages:** If no value is present (`None` is sent as an empty payload `""`)

#### Receiving and Processing Payloads

When a message is received:

- The function `on_message` stores the decoded payload and timestamp in the message store.
- If the payload is a JSON object, individual attributes may be extracted and distributed to subtopics (`_extract_attributes_from_payload_and_update_store`).
- The function `_extract_payload_value` converts the payload to the appropriate Python type (e.g., number, dict, string). It handles:
  - JSON decoding (automatically detects numbers, booleans, lists, dicts)
  - Extraction of numbers from strings (e.g., `"22.5 °C"` → `22.5`)
  - Returns the raw string if no other format matches

#### Example Topics and Payloads

| Topic                         | Payload                                  | Meaning                                      |
|-------------------------------|------------------------------------------|----------------------------------------------|
| `thermal_storage/t_sen_bot`   | `22.5 °C`                                | Temperature value as number, unit is ignored |
| `thermal_storage/t_sen_set`   | `{"value": 45}`                          | Setpoint as JSON                             |
| `thermal_storage`             | `{"t_sen_bot": 22.5, "t_sen_set": 45}`   | multiple attribute values from an entity     |
| `boiler/status`               | `0`                                      | Heater status as integer                     |
| `controller/pb_heat_on`       | `{"value": 1}`                           | recommended heater status as JSON            |

### Outputs

Only **attributes** are supported for this interface; commands are not supported as there would be no meaningful difference.

#### Data Transfer Formats

You can configure different ways to send data for each output attribute by adding the `mqtt_format` information. The following formats are supported:

| MQTT Format (`mqtt_format`) | Topic | Payload | Note |
|-----------------------------|-------|---------|------|
| `plain` | `${MQTT_TOPIC_PREFIX}/${entity.id_interface}/${attribute.id_interface}` | `${attribute.value}` / `0` | A plain value with a topic combining the topic prefix and the `id_interface` of the entity and attribute. |
| `fiware-attr` | `${MQTT_TOPIC_PREFIX}/${entity.id_interface}/attrs` | `{"${attribute.id_interface}": ${attribute.value}, "TimeInstant": "${attribute.timestamp}"}` / `{"example_attribute": 0.0, "TimeInstant": "2025-10-10T13:15:45.286235Z"}` | A FIWARE attribute with a JSON-formatted payload. [FIWARE Documentation](https://fiware-zone.readthedocs.io/es/stable/iot-over-mqtt.html) / [FIWARE IoT Agent JSON](https://fiware-iotagent-json.readthedocs.io/en/latest/usermanual.html#mqtt-binding) |
| `fiware-cmdexe` | `${MQTT_TOPIC_PREFIX}/${entity.id_interface}/cmdexe` | `{"${attribute.id_interface}": ${attribute.value}}` / `{"example_attribute": 0.0}` | An acknowledgment for a FIWARE command with a JSON-formatted payload. [FIWARE Documentation](https://fiware-zone.readthedocs.io/es/stable/iot-over-mqtt.html) / [FIWARE IoT Agent JSON](https://fiware-iotagent-json.readthedocs.io/en/latest/usermanual.html#mqtt-binding) |
| `template_${YOUR_NAME}` | Defined in the template under the `topic` key | Defined in the template under the `payload` key | Topic and payload are defined by the template(s). |

#### Custom Templates

You can use custom templates by specifying `template_${YOUR_NAME}` as the `mqtt_format`. The template must be provided using the environment variable `MQTT_TEMPLATE_${YOUR_NAME}`. This variable should contain either a dictionary or a path to a JSON file with the template as a dictionary.

The template configuration requires two keys:

- `topic`: Template for the MQTT topic.
- `payload`: Template for the MQTT payload.

In the templates you could use placeholders to add the results (attributes):

- **Topic Template:**
  - `__OUTPUT_ENTITY__`: Replaced with the `id_interface` of the output entity.
  - `__OUTPUT_ATTRIBUTE__`: Replaced with the `id_interface` of the output attribute.
  - `__MQTT_TOPIC_PREFIX__`: Replaced with the environment variable `MQTT_TOPIC_PREFIX`

- **Payload Template:**
  - `__OUTPUT_ENTITY__`: Replaced with the `id_interface` of the output entity.
  - `__OUTPUT_ATTRIBUTE__`: Replaced with the `id_interface` of the output attribute.
  - `__OUTPUT_VALUE__`: Replaced with the value of the output attribute.
  - `__OUTPUT_UNIT__`: Replaced with the unit of the output attribute.
  - `__OUTPUT_TIME__`: Replaced with the timestamp of the output attribute.

You can use multiple templates by specifying different template names. See the example template [here](./example_mqtt_template.json).

#### Payload Types

The payload values can be of different types. The function `prepare_payload_for_publish` ensures that all payloads are converted to a valid string format for MQTT publishing.

#### Notes for Custom Services

- Topics should be constructed consistently and uniquely.
- Each entity should have its own topic.
- Payloads should preferably be sent as JSON or primitive values.
- For complex payloads (e.g., multiple values in a dict), the internal logic processes as if they had been received from their own subtopics.

---

## File

Data exchange with via local file.

- Read input data from a file (Note: only `.csv` and `.json` is supported currently)
  - csv characteristics:
    - It can be used for single-input data (`value`) and time series (`timeseries`).
    - Name column of time = "Time", Time in ISO format or a compatible format: <https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat>
    - csv separator = ";"
    - decimal= ","
    - Column name (specific input) in `.csv` must be the like `${Attribute-id_interface}` from the config (Important: the IDs of the attributes `id_interface` over the the interface "file" must therefore be unique)
    - An example of this input is attached as [inputs_csv-file_interface_example.csv](./inputs_csv-file_interface_example.csv), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)
  - json characteristics:
    - It can be used for single-input data (`value`)
    - json object contains a list of dicts
      - id of entity
      - attributes:
        - `attribute_id`
        - `value`
        - `unit`: As part of DataUnits / optional
        - `time`: Time in ISO format or a compatible format: <https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat> / optional
    - An example of this input is attached as [inputs_json-file_interface_example.json](./inputs_json-file_interface_example.json)
- Read static data from a local file (Note: only `.json` is supported currently)
  - The same structure is used as for the input data from the JSON file.
  - An example of this static data is attached as [static_data.json](./static_data.json), could be used by the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)
- Write data to a results file (`.json`)
  - send results of the service to file (for each entity) and timestemp
  - same structure like the `inputs.json`
  - An example of this outputs is attached as [outputs_dhw_calculation_example.json](./outputs_dhw_calculation_example.json), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)

necessary ENV's with example:

  ```
  PATH_OF_INPUT_FILE = "path_to_the_file/validation_data.csv"
  PATH_OF_STATIC_DATA = "path_to_the_file/static_data.json"
  START_TIME_FILE = "2023-01-01 00:00"  # Default / It needs to be ISO compatible (https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat).
  PATH_OF_RESULTS = "./results" # The folder for storing the results is "./results" by default.
  ```
