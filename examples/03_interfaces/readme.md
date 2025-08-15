# Interfaces for data exchange

It is possible use different interfaces for the data exchange:

- FIWARE-API
- MQTT
- File

## FIWARE-API

Data exchange with the data platform of the N5GEH / FIWARE platform using the following APIs

- Contextbroker Orion
  - retrieve the existing entities and attributes as well as the current data of each entity
  - return the output (attributes / commands)
- Time Series Database CrateDB
  - query time series
  - use more stable than FIWARE-GE Quantumleap

- The base service uses the [FiLiP](https://github.com/RWTH-EBC/FiLiP/tree/master/examples) Python library and standard FIWARE APIs. It is possible to connect to platforms with or without authentication, you need to adjust the environment variables.

## MQTT

### Topics

MQTT topics in EnCoDaPy are dynamically constructed for each input entity using:

- A topic prefix from the .env (e.g., `project/mysuperproject/`)
- The entity ID(_interface) (`entity.id_interface`)
- The attribute ID(_interface) (`attribute.id_interface`)

**Example topic:**

```
project/mysuperproject/thermal_storage/t_sen_bot
```

### Message Store Structure

For each topic, the internal message store (`self.mqtt_message_store`) maintains:

- `entity_id`: The ID of the entity
- `attribute_id`: The ID of the attribute (optional)
- `payload`: The current value (e.g. measurement, status, a dict)
- `timestamp`: The time of the last update

If the service tries to `get_data` from an mqtt-attribute, it retrieves the latest value for the attribute from the internal MQTT message store (self.mqtt_message_store), extracts and converts the payload using the configured logic, and returns the result as part of the InputDataModel. If no value is available, the attribute is marked as unavailable.

### Payloads

Payloads sent and received via MQTT can have various formats:

- **Primitive values:** `int`, `float`, `str`, `bool` (e.g., `"22.5"`, `"on"`, `0`)
- **JSON objects:** Dictionaries or lists, e.g., `{"value": 42, "unit": "°C"}`
- **DataFrames:** Serialized as JSON strings
- **Empty messages:** If no value is present (`None` is sent as an empty payload `""`)

The function `prepare_payload_for_publish` ensures that all payloads are converted to a valid string format for MQTT publishing.

### Receiving and Processing Payloads

When a message is received:

- The function `on_message` stores the decoded payload and timestamp in the message store.
- If the payload is a JSON object, individual attributes may be extracted and distributed to subtopics (`_extract_attributes_from_payload_and_update_store`).
- The function `_extract_payload_value` converts the payload to the appropriate Python type (e.g., number, dict, string). It handles:
  - JSON decoding (automatically detects numbers, booleans, lists, dicts)
  - Extraction of numbers from strings (e.g., `"22.5 °C"` → `22.5`)
  - Returns the raw string if no other format matches

### Example Topics and Payloads

| Topic                         | Payload                                  | Meaning                                      |
|-------------------------------|------------------------------------------|----------------------------------------------|
| `thermal_storage/t_sen_bot`   | `22.5 °C`                                | Temperature value as number, unit is ignored |
| `thermal_storage/t_sen_set`   | `{"value": 45}`                          | Setpoint as JSON                             |
| `thermal_storage`             | `{"t_sen_bot": 22.5, "t_sen_set": 45}`   | multiple attribute values from an entity     |
| `boiler/status`               | `0`                                      | Heater status as integer                     |
| `controller/pb_heat_on`       | `{"value": 1}`                           | recommended heater status as JSON            |

### Notes for Custom Services

- Topics should be constructed consistently and uniquely.
- Each entity should have its own topic.
- Payloads should preferably be sent as JSON or primitive values.
- For complex payloads (e.g., multiple values in a dict), the internal logic processes as if they had been received from their own subtopics.

## File

Data exchange with via local file.

- Read input data from a file (Note: only `.csv` and `.json` is supported currently)
  - Read Input values for the actual (simulation) time of configured input from file
  - csv characteristics:
    - Name column of time = "Time"
    - csv separator = ";"
    - decimal= ","
    - Column name (specific input) in `.csv` must be the like `${Attribute-id_interface}` from the config (Important: the IDs of the attributes `id_interface` over the the interface "file" must therefore be unique)
    - An example of this input is attached as [inputs_csv-file_interface_example.csv](./inputs_csv-file_interface_example.csv), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)
  - json characteristics:
    - json object contains a list of dicts
    - key of timestamp = "time"
    - key name (specific input) in `.json` must be the like `${Attribute-id_interface}` from the config (Important: the IDs of the attributes `id_interface` over the the interface "file" must therefore be unique)
    - An example of this input is attached as [inputs_json-file_interface_example.json](./inputs_json-file_interface_example.json), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)
- Read static data from a local file (Note: only `.json` is supported currently)
  - json characteristics:
    - json object contains a list of dicts
    - key name (specific static data) in `.json` must be the like `${staticdata-id}` from the config (Important: the IDs of the attributes `id` over the the interface "file" must therefore be unique)
    - An example of this static data is attached as [static_data.json](./static_data.json), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)
- Write data to a results file (`.json`)
  - send results of the service to file (for each entity) and timestemp
  - An example of this outputs is attached as [outputs_dhw_calculation_example.json](./outputs_dhw_calculation_example.json), using the the configuration from [n5geh.encodapy/examples/01_config/config.json](./../01_config/config.json)

nessesary ENV's with example:

```
PATH_OF_INPUT_FILE = "../validation_data.csv"
START_TIME_FILE = "01.01.2023 06:00"
TIME_FORMAT_FILE = "%d.%m.%Y %H:%M"
```
