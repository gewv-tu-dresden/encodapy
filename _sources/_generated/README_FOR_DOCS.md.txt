# "EnCoDaPy" – Energy Control and Data Preparation in Python

[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://gewv-tu-dresden.github.io/encodapy/)
[![Python Versions](https://img.shields.io/pypi/pyversions/encodapy.svg)](https://pypi.org/project/encodapy/)
[![PyPI version](https://img.shields.io/pypi/v/encodapy)](https://img.shields.io/pypi/v/encodapy)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21130217.svg)](https://doi.org/10.5281/zenodo.21130217)
[![Pylint](https://github.com/gewv-tu-dresden/encodapy/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/gewv-tu-dresden/encodapy/actions/workflows/pylint.yml)
[![Tests](https://github.com/gewv-tu-dresden/encodapy/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/gewv-tu-dresden/encodapy/actions/workflows/tests.yml)

## Overview

- The Basic Service provides a system to
  - read a configuration
  - receive data
  - start a calculation
  - return the results
- This interaction is possible with several interfaces, see [examples/03_interfaces](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples/03_interfaces):
  - FIWARE-API
  - MQTT
  - File
- The controller has the functionality to read a configuration from JSON and ENV, validate it and return it as a model.
- The framework provides components that can be used within a service. This is the recommended solution for running a functional service.
  For more information and code, see: [encodapy/components/readme.md](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/components/readme.md)

- Further documentation can be found [here](https://gewv-tu-dresden.github.io/encodapy/).
- Examples and documentation for each part of the project are available under: [examples](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples)

## Configuration

- The configuration of the service must be provided via `config.json` and has several sections (see the [documentation](https://gewv-tu-dresden.github.io/encodapy/basic_service.html) or the [examples](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples)):
  - `name`: Controller name - for documentation purposes only
  - `interfaces`: Indicates which interfaces are active
  - `inputs`: Configuration of the inputs to the controller
  - `outputs`: Configuration of the outputs
  - `staticdata`: Static data point configuration (Data that is not continuously updated)
  - `controller_components`: Configuration of the controller components, see [encodapy/components/readme.md](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/components/readme.md) or the [documentation](https://gewv-tu-dresden.github.io/encodapy/components.html)
  - `controller_settings`: General settings about the controller

- Environmental variables are required to configure the basic service and the interfaces. For more information, see [encodapy/config/env_values](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/config/env_values.py) or the [documentation](https://gewv-tu-dresden.github.io/encodapy/).

## Usage

You could install the Package via [PyPI](https://pypi.org/project/encodapy/):

```
pip install encodapy
```

There are two ways to use the Package:

### Customer service based on the ControllerBasicService

To create your own custom service, you have to overwrite two functions of the [ControllerBasicService](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/service/basic_service.py):

- `prepare_start()`: This is a synchronous function that prepares the start of the algorithm and specifies aspects of the service. This should not take long due to health issues in Docker containers. It only needs to be overwritten if other tasks are required after initialisation of the service.
- `calculation()`: Asynchronous function to perform the main calculation in the service
- `calibration()`: Asynchronous function to calibrate the service or coefficients and update StaticData in the service if only required

To start the service, you need to call

- `start_calibration()`: To start the calibration if required
- `start_service()`: To start the service

For more details, see the [examples](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples)

### Run Components with the ComponentRunnerService

- You could use components to run them with the [ComponentRunnerService](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/service/component_runner_service.py)
- Frist, create a configuration, then start the service:
  - as shown in [examples/07_component_runner](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples/07_component_runner)
  - by running the service with the [encodapy.service.service_main](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/service/service_main.py) function.
- If you need additional components, please see [encodapy/components](https://github.com/gewv-tu-dresden/encodapy/blob/main/encodapy/components):
  - You can use components from `encodapy/components` or create your own
  - An easy way to build your own component is shown in [examples/08_create_new_component](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples/08_create_new_component)

### Examples

For different examples and documentation, how to use the tool - see [examples](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples).

The examples are intended to help you use the tool and understand how it works:

- the configuration
- the use
- the components

### Units

- Inputs and outputs get information about the unit. The class [`DataUnits`](https://github.com/gewv-tu-dresden/encodapy/blob/main/controller_software/utils/units.py) is used for this.
- More units must be added manually.
- Timeranges:
  - Timeranges for data queries are different for calculation and calibration.
  - The following timeranges are possible
    - '"minute"'
    - '"hour"'
    - '"day"'
    - '"month"' (30 days for simple use)
- Inputs and outputs can be adjusted between compatible units via the central unit conversion logic.

### Deployment

The recommended way to run the service is:

- Create a Python environment using Poetry (see [pyproject.toml](https://github.com/gewv-tu-dresden/encodapy/blob/main/pyproject.toml)).
- For production deployments, use the [Dockerfile](https://github.com/gewv-tu-dresden/encodapy/blob/main/Dockerfile) or the official Docker image.
- Use [dockerfile.dev](https://github.com/gewv-tu-dresden/encodapy/blob/main/dockerfile.dev) for local development in Docker.

Example commands:

```bash
docker buildx build --platform linux/amd64 --target production -t encodapy:prod --load .
docker buildx build --platform linux/amd64 -t encodapy:dev --load -f Dockerfile.dev .
```

There are examples of how to use the image in [examples/07_component_runner](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples/07_component_runner) and [examples/05_simple_service_mqtt](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples/05_simple_service_mqtt). The working directory in the production image is `/app`, so you need to either mount the necessary files or change the environmental variables. See the documentation.

### Testing Notes

- Solver-based Flixopt integration tests depend on optional runtime packages (for example highspy).
- If those optional packages are unavailable, solver-based tests are skipped.

## References

If you use EnCoDaPy in your research or project, please cite [https://doi.org/10.5281/zenodo.21130217](https://doi.org/10.5281/zenodo.21130217) or the version of the software currently in use.

## License

This project is licensed under the BSD License - see the [LICENSE](https://github.com/gewv-tu-dresden/encodapy/blob/main/LICENSE) file for details.

## Copyright

<a href="https://tu-dresden.de/ing/maschinenwesen/iet/gewv"> <img alt="TUD GEWV" src="https://raw.githubusercontent.com/gewv-tu-dresden/encodapy/main/docs/source/logos/GEWV_Logo.svg" height="75"> </a>

2024-2026, TUD Dresden University of Technology, Chair of Building Energy Systems and Heat Supply

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
