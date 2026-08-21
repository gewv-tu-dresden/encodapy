---
title: 'EnCoDaPy: A python Framework for Energy Control and Data Preparation'
tags:
  - Python
  - IoT
  - Pydantic
  - Platform
  - Energy Management
  - Data Analysis

authors:
  - name: Martin Altenburger
    orcid: 0009-0003-0823-8582
    affiliation: 1
    corresponding: true
  - name: Maximilian Beyer
    orcid: 0000-0003-0180-8143
    affiliation: 1 
  - name: Paul Seidel
    orcid: 0009-0004-7903-8411
    affiliation: 1
affiliations:
  - name: Chair of Building Energy Systems and Heat Supply, TUD Dresden University of Technology, Germany
    index: 1

date: xx September 2026
bibliography: paper.bib

# Optional fields for papers that are part of a joint submission.
# For example, submitting to a AAS journal too, see this blog post:
# https://blog.joss.theoj.org/2018/12/a-new-collaboration-with-aas-publishing
#
# If you are not making a joint submission you should remove these lines.
#

# Example see https://joss.readthedocs.io/en/latest/example_paper.html
# aas-doi:  <- update this with the DOI from AAS once you know it.
# aas-journal:  <- The name of the AAS journal.
---


# Summary

EnCoDaPy is a Python framework for energy data processing and control that offers a modular architecture for developing services for data acquisition, calculation, and result reporting. The framework supports multiple interfaces, such as the FIWARE API, MQTT, and file systems, and is specifically designed for applications in energy research. The framework is designed to enable rapid implementation of new algorithms, as these can be integrated into individual components. Core features such as communication, configuration loading and the execution of the calculation cycle are already predefined and ready for use. This significantly reduces the implementation effort and ensures modular reusability.

The central starting point is the use of the open-source FIWARE platform, which provides a key capability for data management [@cirillo_2019; @blechmann_2023]. EnCoDaPy can be integrated within a cloud environment via a FIWARE instance and in decentralized applications using MQTT.

# Statement of need

The increasing integration of decentralized energy producers, storage systems, and flexible consumers requires software capable of collecting and processing energy data from heterogeneous sources and exchanging it among distributed components. For research and prototyping applications, data acquisition, configuration management, validation, calculations, and communication often need to be flexibly integrated. Communication interfaces such as MQTT and FIWARE provide important mechanisms for this purpose, but they do not handle the application-specific processing and calculation of energy data.

EnCoDaPy addresses this need as a modular, open-source Python framework for energy management, energy data processing, and control applications. The framework provides a common base service for configuration, data acquisition, calculation, and the transmission of results. Application-specific functions can be implemented, reused, and extended using configurable components. Both current-state data and historical time series can be processed.

# State of the field 

Existing approaches address various aspects of decentralized energy systems, including agent-based control, optimization, simulation, resource allocation, energy trading, and scheduling. The following \autoref{tab:comparison} compares selected approaches in terms of their communication interfaces, architectural concepts, data processing capabilities, and open-source status. This analysis considers two publications describing software frameworks with publicly available implementations (AgentLib [@eser_2025] and NeuraFlux [@desage_2025]) and two scientific articles that describe application-specific multi-agent energy systems ([@davoudi_2024; @blaauwbroek_2015]). The selected references represent categories relevant to EnCoDaPy, including agent-based energy frameworks, simulation-oriented software, and application-specific, multi-agent energy management systems (EMS). This comparison is intended to illustrate the position of EnCoDaPy within the broader software landscape rather than to provide a complete benchmark of individual features.

| Software / reference                                    | Communication and integration mechanisms                                      | System design                            | Data and processing scope                                      | Type                                                                     |
| :------------------------------------------------------ | :---------------------------------------------------------------------------- | :------------------------------------------- | :------------------------------------------------------------- | :----------------------------------------------------------------------- |
| EnCoDaPy                                                | MQTT, FIWARE and file-based interfaces                                        | Modular and extensible framework         | current-state and historical time-series data                  | Open-source framework [@altenburger_encodapy_2026]; BSD-3-Clause license |
| AgentLib [@eser_2025]                                   | Local, MQTT, FIWARE (via Plugin)                                              | Modular, component-based agent framework | current-state and historical time-series data, simulation data | Open-source framework [@esser_agentlib_2025]; BSD-3-Clause license       |
| NeuraFlux [@desage_2025]                                | Internal Python-functions; external integrations described but not identified | Modular agent-based architecture         | current-state and historical simulation data                   | Open-source framework [@desage_neuraflux_2025]; Apache-2.0 license       |
| EMS using multi-agent systems [@davoudi_2024]           | CANopen                                                                       | Hierarchical multi-agent system          | current simulation data;  measurement data not reported        | Application-specific research system                                     |
| Multi-Commodity Smart Energy System [@blaauwbroek_2015] | Agent-based communication; Java Agent Development Framework (JADE)            | Distributed multi-agent system           | current simulation data; schedule exchange                     | Application-specific research system                                     |

Table: Comparison of EnCoDaPy with related energy-management frameworks. \label{tab:comparison}

Both EnCoDaPy and AgentLib address some of the same requirements for energy system software, including modular components, data communication and the processing of current-state and historical data. EnCoDaPy was developed as a separate codebase within the N5GEH research consortium and in parallel with related developments such as AgentLib. Its aim is to support configuration-driven, cyclic data processing and control services for real or emulated energy systems. Therefore, the two projects represent parallel developments of related concepts and are not direct extensions or reimplementations of one another.

Although both frameworks use modular architectures and support communication mechanisms or integrations such as MQTT and FIWARE, their design priorities differ. AgentLib offers a general, modular framework for agent-based energy applications which supports control, optimization, simulation and communication. It also provides an interface to the FIWARE API [@eser_2025] and supports the integration of simulation models through Functional Mock-up Units [@esser_agentlib_2025].  EnCoDaPy, in contrast, provides a common runtime environment for configuration, data acquisition, validation, computation, and result transmission, while application-specific functionality is implemented through configurable components. AgentLib primarily organizes applications around interacting agents and simulation- or communication-oriented components, whereas EnCoDaPy primarily organizes service workflows around the recurring runtime functionality of configurable energy-data services.

NeuraFlux is based on a modular, agent-based architecture and supports the processing of current and historical simulation data [@desage_2025]. Although the publication describes integration with hardware, APIs, and OEM software [@desage_2025], the authors’ analysis of the publicly accessible repository at commit `4c5ebc6` identified no specific, documented interface for importing real-world data from external systems [@desage_neuraflux_2025]. Instead, data exchange in the inspected implementation is performed through internal Python functions. The publication therefore describes a broader intended or conceptual scope than the directly usable external-integration functionality identified in the inspected repository.

Other approaches focus on specific multi-agent energy-management applications, such as resource allocation, energy trading, or schedule generation [@davoudi_2024; @blaauwbroek_2015]. The authors did not identify public code repositories for these approaches in the cited publications or during the repository search conducted for this comparison. Taken together, these approaches illustrate how modular and distributed architectures have been applied to energy system control, scheduling, and resource-allocation problems. The selected references focus primarily on agent-based application frameworks, the integration of simulations, and specific energy management tasks. The selected references focus primarily on agent-based application frameworks, the integration of simulations, or specific energy management tasks, whereas EnCoDaPy emphasizes the combination of a configuration-driven cyclic runtime environment, heterogeneous data interfaces, and reusable application-specific components organized around service workflows.

EnCoDaPy is primarily intended for research and prototyping applications involving data processing and control in real or emulated energy systems. Unlike simulation-oriented frameworks, it does not provide an explicit interface for integrating simulation models. However, simulated or emulated components can be connected via the same interfaces used for real data sources. This allows EnCoDaPy to be used for testing and prototyping without simulation integration being the primary focus.

# Software design

## Main Function

As its name suggests, EnCoDaPy's main function is to facilitate the integration, processing, and control of energy-related data in a modular and scalable way. Designed to connect raw data acquisition, control, and advanced energy system analysis, EnCoDaPy is particularly relevant for smart grid, building energy management, and energy system research and industrial applications using the Internet of Things (IoT) for monitoring and control.
The framework addresses several key challenges in energy data management, primarily focusing on the following aspects:

- Heterogeneous Data Sources  
EnCoDaPy supports multiple interfaces (e.g., FIWARE, MQTT, file-based) to ingest data from diverse sources, ensuring compatibility with existing infrastructure. This enables seamless interaction between multiple EnCoDaPy instances or external systems via standardised interfaces.
- Modularity and Extensibility  
The framework provides a base function that is responsible for configuration and communication. Based on this, a component runner is included which enables components with special functions to be run. The framework also provides some base components for building energy management, such as a thermal storage calculator or a typical thermal controller.
Users can customise and extend the framework by developing their own components or leveraging pre-built modules for specific tasks.
- Processing  
The framework is optimised for current data processing and control, enabling dynamic responses to changing energy conditions. Depending on the computing speed, variable iteration can make it possible to achieve higher speeds in simulations.
- Trusted and unified  
During the runtime of a controller, problems often arise from incorrect configurations. The framework gives you a way to check the configuration when the algorithm starts, based on Pydantic [@colvin_pydantic_2024]. The centralised JSON and environmental values-based configuration ensure consistency and security across deployments. This makes it easier to reuse and extend configurations.
- Processing variable data  
It is possible to process status data as well as historical data. Data can be combined and evaluated according to the specific requirements. Time series or current values/target values can also be output as results.

## Code Sructure

EnCoDaPy is based on a basic (core) service that provides essential functionality for each algorithm, whether for controllers or data preparation. This basic service has been developed as an asynchronous Python application comprising the following subtasks:

- Providing the cyclical service
- Loading and verifying the configuration
- Collecting data from the interfaces
- Running the relevant calculations and providing the results
- Forwarding the data and ensuring the configured information

The basic service enables the creation of a Python service based on this fundamental functionality, with no constraints on the calculation itself. The functions of the basic service are shown as a flow chart in \autoref{fig:schema_basic_service_sequenz}.

![Flow chart of the EnCoDaPy-Service \label{fig:schema_basic_service_sequenz}](./schema_basic_service_sequenz.pdf)

The core functions are handled by:

- `ControllerBasicService`  
  This class provides the basic implementation of configuration, interfaces, and cyclic processing. For specific use of the framework, the `calculation()` and `calibration()` functions can be used to integrate custom algorithms for calculation and calibration of that calculation.

  EnCoDaPy uses asynchronous execution for communication via MQTT or with the FIWARE API, ensuring that these operations are non-blocking. Additionally, calculation (`calculation()`) and calibration (`calibration()`) are also performed asynchronously. This enables concurrent background processes (e.g., periodic calibration) and flexible user implementations using asynchronous libraries. The architecture is therefore well-suited for EMS that must continuously process data while simultaneously adjusting parameters.

- `ComponentRunnerService`  
  This second class builds on the `ControllerBasicService` and provides a way to simplify the use of the previously mentioned functions. It introduces the ability to use `Components` and provides the necessary foundation for doing so. It handles the mapping of input and output data and performs an automatic configuration check. This approach thus facilitates easy reusability, since components can be activated, deactivated, and replaced through configuration and must adhere to a defined structure.

## Configuration

The configuration is divided into a main configuration from a file, which is easy to read thanks to its JSON structure, and environmental variables for access credentials. This allows secrets to be handled in a secure way. The main configuration has different parts for each important part of a service based on EnCoDaPy. The structure, including an overview of the function, is shown in \autoref{fig:schema_basic_config}.

![Schema of the basic configuration \label{fig:schema_basic_config}](./schema_basic_config.pdf)

Verification is performed while loading the configuration using the solutions from Pydantic [@colvin_pydantic_2024]. This means that any configuration-related issues will be logged, and the service will stop if necessary. This ensures that the service will not crash later due to these issues. Using Pyndatic [@colvin_pydantic_2024] BaseModel makes it easy to document the configuration and use the variables in the code without encountering any type issues.

## Interfaces

Collecting data and returning the results can be time-consuming due to the variety of data endpoints. The basic service provides the ability to connect to different interfaces and manage data exchange with these interfaces. Interfaces that are often used are:

- MQTT: Direct exchange via MQTT messages.
- FIWARE: connecting to the context broker of a FIWARE platform ensures the availability of status values and historical time series.
- FILE: Reading or writing data to a file allows data connections to be integrated via file exchange or for default variables to be stored locally.

To use these interfaces, they only need to be activated in the configuration, along with the datapoints (input and output data). A combination of interfaces is possible.

## Components

EnCoDaPy's component architecture builds on the basic service, creating a modular, scalable solution for energy data processing. Components perform specific calculations and standardize data processing, reducing implementation effort while enabling flexible exchange. The ComponentRunnerService improves upon the basic flow (see \autoref{fig:schema_basic_service_sequenz}) by initializing components from the configuration file and executing them sequentially with automatic data exchange.

### Using and Creating Components

The component runner enables creating a Python service for data preparation or energy management by configuring existing components or building custom ones. Components require:

- Input/output configuration (and optionally parameter configuration)
- A `calculate()` method to compute results

All components must follow this consistent template for "new_component".

```text
<new_component>/
├── __init__.py                 # can be empty
├── new_component.py            # initialises the class NewComponent
└── new_component_config.py     # contains all necessary configurations
```

The `new_component_config.py` defines the configuration of inputs, outputs, and parameters, while `new_component.py` implements the algorithm with a `calculate()` method.

```python

from encodapy.components.basic_component import BasicComponent
from .new_component_config import (
    NewComponentOutputData
)

class NewComponent(BasicComponent):

    def calculate(self) -> None:
        """Perform calculations and set self.output_data"""
        self.output_data = NewComponentOutputData(
            result=self.compute_result()
        )

```

EnCoDaPy includes components for calculating thermal storage energy and optimizing model-predictive control, which addresses common energy management needs.

### Thermal Storage Component

The Thermal Storage Component provides a temperature-based estimate of the state of charge of a multi-layer thermal storage tank. It models a tank divided into $n$ layers, each with an individual temperature. It then computes the normalized state of charge, $\varphi_\mathrm{TS}$, as a mass-weighted sum of the layer-specific temperatures (see Eq. \autoref{eq:ts_varphi}). This estimate assumes a constant heat capacity and is valid for temperatures between the layer-specific reference bounds ($\vartheta_\mathrm{TS~R~i}$​) and the nominal bounds ($\vartheta_\mathrm{TS~N~i}$​). Calibration against measurement data or a physical reference model is necessary to achieve exact thermodynamic energy content.

\begin{equation}\label{eq:ts_varphi}
\varphi_\mathrm{TS} = \sum_{i}^{n_{\mathrm{TS}}}
\frac{m_i}{m_{\mathrm{TS}}} \cdot
\frac{\vartheta_{\mathrm{TS}\,i} - \vartheta_{\mathrm{TS}\,\mathrm{R}\,i}}
     {\vartheta_{\mathrm{TS}\,\mathrm{N}\,i} - \vartheta_{\mathrm{TS}\,\mathrm{R}\,i}}
\end{equation}

Here, $m_\mathrm{TS}$ denotes the total storage mass, where $m_{\mathrm{TS}} = \sum_{i=1}^{n_{\mathrm{TS}}} m_i$.

### FlixOpt Model Component

The flixOpt Model Component combines the flixOpt optimization framework [@panitz_2022; @bumann_flixopt_2026] with EnCoDaPy, allowing for operational optimization without manual setup. The component uses HiGHS as the default solver, though Gurobi is optional and is selected based on the complexity of the model and the required solve speed. The component validates configurations, aggregates incoming time series into an internal DataFrame, and constructs and solves a flixOpt FlowSystem. The results are automatically mapped to EnCoDaPy output data points (e.g., `{storage_label}_soc`, `{converter_label}_thermal_power`). The responsibilities between EnCoDaPy and flixOpt are divided as shown in \autoref{tab:flixopt}.

| Task                     |      EnCoDaPy      |     flixOpt      |
| ------------------------ | :----------------: | :--------------: |
| Input data acquisition   |         x          |                  |
| Time series aggregation  |         x          |                  |
| Model description        | x(via config/JSON) |                  |
| Optimization model       |                    |        x         |
| Solver invocation        |                    | x (HiGHS/Gurobi) |
| Result mapping           |         x          |                  |
| External system transfer |         x          |                  |

Table: Responsibilities between EnCoDaPy and flixOpt in flixOpt Model Component \label{tab:flixopt}

This component could be used as MPC in building management systems (EMS), where it automatically maps sensor data to the flixOpt inputs and optimization results to the control signals.

# Research Impact Statement

The EnCoDaPy framework was developed as part of the N5GEH research consortium and has been used in several satellite projects. The following use cases demonstrate its effectiveness in data analysis and the operational management of building energy systems:

- Virtual sensor technology (domestic hot water (DHW) system):  

  EnCoDaPy was used to analyze measurement data from a temperature-maintaining band in order to determine the system’s operating status based on the DHW temperature and the volume of DHW drawn. Through the connection to the FIWARE platform, historical measurement data was retrieved, and a virtual sensor was implemented in real time using cyclic execution. The analyses were tested through simulations and bench tests achieving a maximal temperature estimation error of 2 K. [@altenburger_2024; @seifert_n5geh-twe-flex_2025]

- Operations Management (Heat Generation):  

  Building on the virtual sensor mentioned above, the framework was used in a simulation to control a heat generator for domestic hot water heating, reducing heat losses from the thermal storage by 11.5 % [@altenburger_2026; @seifert_n5geh-twe-flex_2025].
  In another project combining a pellet boiler and a heat pump, the framework was used in a field test, to specify the operating states of both heat generators with a cycle time of 10 s [@beyer_2026].

- Cloud/Edge Operation (District Heating + PV):

  For a building connected to district heating and equipped with on-site PV generation, EnCoDaPy enabled cloud-based schedule generation and its local implementation at the substation, including data aggregation via the Thermal Storage component. The analyses were conducted using simulation and on a test bench demonstrating schedule-based substation operation and increasing PV self-consumption from 1 % to 2 %. [@seidel_2024]

These projects demonstrate the flexible and practical applicability of EnCoDaPy in various research contexts. As an open-source framework, it promotes reproducibility and interoperability (including through FIWARE integration) in research on building energy systems.

# Conclusion

EnCoDaPy is an open-source Python framework designed to enhance the processing and control of energy data, accelerating research and prototyping in energy systems. Its modular architecture, asynchronous execution, and reusable components enable rapid development of applications for data acquisition, calculation, and operational management.

The framework supports FIWARE, MQTT, and file-based interfaces, which enable the integration of heterogeneous data sources and the processing of both real-time and historical data. Pre-built components for thermal storage modeling and model-predictive control reduce implementation effort even further.

EnCoDaPy is designed for research and prototyping in smart grids, building energy management, and decentralized energy systems. Its modularity reduces implementation effort and enables the reuse of algorithms for real or emulated components.

# AI usage disclosure

Generative AI tools were used in the development and creation of this work as follows:

- Code validation and review:  
  Assistance in checking and validating code snippets, including as a tool for pull request reviews.
  The following were used: GitHub Copilot; You.com with Claude Opus; Vibe (formerly Le Chat) by Mistral AI
- Test development: Assistance in generating tests, which were subsequently reviewed and verified by the authors.
  The following were used: GitHub Copilot; You.com with Claude Opus
- Manuscript: Assistance in revising the paper’s language and structure.
  The following were used: You.com with Claude Opus; GitHub Copilot; DeepL

All AI-generated content (code, tests, text) was reviewed, adapted, and approved by the authors.

# Acknowledgements

The authors gratefully acknowledge the financial support provided by  the German Federal Ministry for Economic Affairs and Energy for the research projects N5GEH-Serv (grant number 03EN1030A) and E³ (grant number 03EN3058C)

# References
