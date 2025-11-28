# "EnCoDaPy" – Energy Control and Data Preparation in Python

## Overview

- The Basic Service provides a system to
  - read a configuration
  - receive data
  - start a calculation
  - return the results
- This interaction is possible with several interfaces, see [examples/03_interfaces](./examples/03_interfaces/):
  - FIWARE-API
  - MQTT
  - File
- The controller has the functionality to read a configuration from JSON and ENV, validate it and return it as a model.
- The framework provides components that can be used within a service. This is the recommended solution for running a functional service.
  For more information and code, see: [encodapy/components/readme.md](./encodapy/components/readme.md)

- Further documentation can be found [here](https://gewv-tu-dresden.github.io/encodapy/).
- Examples and documentation for each part of the project are available under: [examples](./examples/)

## Configuration

- The configuration of the service must be provided via `config.json` and has several sections (see the [documentation](https://gewv-tu-dresden.github.io/encodapy/basic_service.html) or the [examples](./examples)):
  - `name`: Controller name - for documentation purposes only
  - `interfaces`: Indicates which interfaces are active
  - `inputs`: Configuration of the inputs to the controller
  - `outputs`: Configuration of the outputs
  - `staticdata`: Static data point configuration (Data that is not continuously updated)
  - `controller_components`: Configuration of the controller components, see [encodapy/components/readme.md](./encodapy/components/readme.md) or the [documentation](https://gewv-tu-dresden.github.io/encodapy/components.html)
  - `controller_settings`: General settings about the controller

- Environmental variables are required to configure the basic service and the interfaces. For more information, see [encodapy/config/env_values](./encodapy/config/env_values.py) or the [documentation](https://gewv-tu-dresden.github.io/encodapy/).


## Usage

You could install the Package via [PyPI](https://pypi.org/project/encodapy/):

```
pip install encodapy
```

There are two ways to use the Package:

### Customer service based on the ControllerBasicService

To create your own custom service, you have to overwrite two functions of the [ControllerBasicService](./encodapy/service/basic_service.py):

- `prepare_start()`: This is a synchronous function that prepares the start of the algorithm and specifies aspects of the service. This should not take long due to health issues in Docker containers. It only needs to be overwritten if other tasks are required after initialisation of the service.
- `calculation()`: Asynchronous function to perform the main calculation in the service
- `calibration()`: Asynchronous function to calibrate the service or coefficients and update StaticData in the service if only required

To start the service, you need to call

- `start_calibration()`: To start the calibration if required
- `start_service()`: To start the service

For more details, see the [examples](./examples)

### Run Components with the ComponentRunnerService

- You could use components to run them with the [ComponentRunnerService](./encodapy/service/component_runner_service.py)
- Frist, create a configuration, then start the service:
  - as shown in [examples/07_component_runner](./examples/07_component_runner/)
  - by running the service with the [encodapy.service.service_main](./encodapy/service/service_main.py) function.
- If you need additional components, please see [encodapy/components](./encodapy/components/):
  - You can use components from `encodapy/components` or create your own
  - An easy way to build your own component is shown in [examples/08_create_new_component](./examples/08_create_new_component/)

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
- Use a Docker container for production deployments (create a custom image using the [dockerfile](./dockerfile)).

## License

This project is licensed under the BSD License - see the [LICENSE](./LICENSE) file for details.

## Copyright

<a href="https://tu-dresden.de/ing/maschinenwesen/iet/gewv"> <img alt="TUD GEWV" src="https://raw.githubusercontent.com/gewv-tu-dresden/encodapy/main/docs/source/logos/GEWV_Logo.svg" height="75"> </a>

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

We gratefully acknowledge the financial support of the Federal Ministry for Economic Affairs and Energy.

<a href="https://www.bundeswirtschaftsministerium.de/Navigation/EN/Home/home.html"> <img alt="BMWE"
src="https://raw.githubusercontent.com/gewv-tu-dresden/encodapy/main/docs/source/logos/BMWE_gefoerdert_en_RGB.svg" style="height:200px; width:auto; max-width:none;"> </a>
