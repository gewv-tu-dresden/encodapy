# "EnCoDaPy" – Energy Control and Data Preparation in Python.

## Overview
- The Basic Controller provides a system for 
    - read a configuration
    - receive data
    - start a calculation
    - return the results
- This interaction is possible with several interfaces, see [examples/03_interfaces](./examples/03_interfaces/):
    - FIWARE-API
    - MQTT
    - File
- The controller has the functionality to read a configuration from JSON and ENV, validate it and return it as a model.
- The framework provides components that can be used within a service.  
  For more information and code, see: [encodapy/components/README.md](./encodapy/components/README.md)

- Examples and documentation for each part of the project are available under: [examples](./examples/)


## Configuration
- The configuration of the service must be provided via `config.json` and has several sections (see the [examples](#examples)):
    - `name`: Controller name - for documentation purposes only
    - `interfaces`: Indicates which interfaces are active
    - `inputs`: Configuration of the inputs to the controller
    - `outputs`: Configuration of the outputs
    - `staticdata`: Static data point configuration (Data that is not continuously updated)
    - `controller_components`: Configuration of the controller components, see [encodapy/components/readme.md](./encodapy/components/readme.md)
    - `controller_settings`: General settings about the controller 

- ENVs are required to configure the interfaces / get the config with the default value [`default`]:
    ```
    CONFIG_PATH =  ["./config.json"]
    LOG_LEVEL =
    RELOAD_STATICDATA = False

    # FIWARE - Interface
    CB_URL = ["http://localhost:1026"]
    FIWARE_SERVICE = ["service"]
    FIWARE_SERVICE_PATH = [/]
    FIWARE_AUTH = [False]
    # only used if FIWARE_AUTH = true / Option 1 for authentication
    FIWARE_CLIENT_ID = 
    FIWARE_CLIENT_PW = 
    FIWARE_TOKEN_URL = 
    # only used if FIWARE_AUTH = true and the three previously not set / Option 2 for authentication
    FIWARE_BAERER_TOKEN = []

    CRATE_DB_URL = ["http://localhost:4200"]
    CRATE_DB_USER = ["crate"]
    CRATE_DB_PW = [""]
    CRATE_DB_SSL = [False]

    # FILE - Interface
    PATH_OF_INPUT_FILE = "path_to_the_file_\\validation_data.csv"
    START_TIME_FILE = "01.01.2023 06:00"
    TIME_FORMAT_FILE = "%d.%m.%Y %H:%M" - format of time in file
    ```

## Usage

You could install the Package via PyPI:
```
pip install encodapy
```
To create your own custom service, you have to overwrite two functions of the [ControllerBasicService](./encodapy/service/basic_service.py):
- `prepare_start`: This is a synchronous function that prepares the start of the algorithm and specifies aspects of the service. This should not take long due to health issues in Docker containers. It only needs to be overwritten if other tasks are required after initialisation of the service.
- `calculation()`: Asynchronous function to perform the main calculation in the service
- `calibration()`: Asynchronous function to calibrate the service or coefficients in the service if only required

To start the service, you need to call
- `start_calibration()`: To start the calibration if required
- `start_service()`: To start the service

A easy posibility to start the service is to run the base [main.py](./service_main/main.py). For more details, see the [examples](#examples)

### Examples
For different examples and documentation, how to use the tool - see [examples](./examples/).

The examples are intended to help you use the tool and understand how it works:
- the configuration
- the use
- the components

### Units
- Inputs and outputs get information about the unit. The class [`DataUnits`](./controller_software/utils/units.py) is used for this.
- More units must be added manually.
- Timeranges:
    - Timeranges for data queries are different for calculation and calibration.
    - The following timeranges are possible
        - '"minute"'
        - '"hour"'
        - '"day"'
        - '"month"' (30 days for simple use)
- Today, there ist no adjustment for different units. Its a TODO for the future

### Deployment
The recommended way to run the service is:
- Create a Python environment using Poetry (see [pyproject.toml](./pyproject.toml)).
- Use a Docker container for production deployments (create a custom image using the [dockerfile](dockerfile)).

## License

This project is licensed under the BSD License - see the [LICENSE](LICENSE) file for details.

## Copyright

<a href="https://tu-dresden.de/ing/maschinenwesen/iet/gewv"> <img alt="EBC" src="https://raw.githubusercontent.com/N5GEH/.github/main/logos/Logo-Banner-TUD-IET-GEWV.jpg" height="75"> </a>

2024-2025, TUD Dresden University of Technology, Chair of Building Energy Systems and Heat Supply

## Related projects

- EnOB: N5GEH-Serv - National 5G Energy Hub <br>
<a href="https://n5geh.de/"> <img alt="National 5G Energy Hub" 
src="https://avatars.githubusercontent.com/u/43948851?s=200&v=4" height="150"></a>

- EnOB: TWE-Flex - Optimisation and flexibilisation of domestic hot water heating systems <br>
<a href="https://n5geh.de/twe-flex/"> Project Website </a>

- EnEff: E³ - Low-emission and energy-efficient energy supply in urban areas using the latest intelligent ICT structures <br>
<a href="https://n5geh.de/e3/"> Project Website </a>

## Acknowledgments

We gratefully acknowledge the financial support of the Federal Ministry for Economic Affairs and Climate Action (BMWK).

<a href="https://www.bmwi.de/Navigation/EN/Home/home.html"> <img alt="BMWK" 
src="https://raw.githubusercontent.com/RWTH-EBC/FiLiP/master/docs/logos/bmwi_logo_en.png" height="100"> </a>
