# FlixOpt Model Component

This component runs a model-based optimization with [FlixOpt](https://flixopt.github.io/flixopt/latest/) and exposes optimization results as EnCoDaPy output datapoints.

It is designed for model-predictive control (MPC) and schedule generation in energy systems. For this reason, the key features from FlixOpt for the MPC are taken to build a simple model. You can build this model via configuration file or add some additional constraints via python function.

## Functionality

The component validates a FlixOpt model definition, builds a FlixOpt `FlowSystem`, solves it with the configured solver, and maps selected result series to output datapoints.

Implemented workflow:

1. Read and validate component configuration (`flixopt_model`, solver, log level).
2. Load FlixOpt model definition, like it is given in den component configuration from:

    - Inline dictionary, or
    - Path to a JSON file.

3. Collect time-series inputs from component inputs and merge them into one internal DataFrame.
4. Build FlixOpt model elements:

    - Buses
    - Effects
    - Converters
    - Storages
    - Sinks / Sources / Bidirectional exchangers

5. Optionally load and execute a custom constraint function.
6. Run optimization.
7. Convert optimization results to EnCoDaPy output datapoints.

## Supported Model Elements

The FlixOpt model schema is implemented in [flixopt_models.py](./flixopt_models.py).

### Converters

Supported converter types (`converter_type`):

- `boiler`: A linear converter representing a gas boiler that transforms an input flow of gas into a thermal output flow at fixed ratios.
- `power2heat`: A linear converter representing a power-to-heat device that transforms an input flow of electrical energy into a thermal output flow with fixed ratios.
- `chp`: A linear converter, representing a combined heat and power unit.
- `substation`: A linear converter representing a substation. It can be used as a transformer between one bus and another.
- `bidirectional_substation`: A special version of a `substation`, this component creates forward and reverse converter representations and adds binary constraints to prevent simultaneous opposite operation.

### Storages

Storages are mapped to FlixOpt storage elements with:

- Charge and discharge flows
- Min/max SOC bounds
- Initial SOC handling
- Efficiency and self-discharge handling

### Exchangers

Supported energy directions:

- `sink`
- `source`
- `bidirectional`

For `bidirectional` exchangers, the component uses `SourceAndSink` with prevention of simultaneous in/out flow.

## Component Configuration

Main configuration model: `FlixoptModelComponentConfigData` in [flixopt_model_component_config.py](./flixopt_model_component_config.py).

Required and optional fields:

- `flixopt_model` (required):
  - Datapoint whose `value` is either:
    - A model dictionary, or
    - A path to a model JSON file.
- `solver_settings` (optional):
  - Solver name (`HighsSolver` or `GurobiSolver`)
  - Optional: `mip_rel_gap`, `time_limit`
- `log_level` (optional):
  - `exploring`, `debug`, `production`, `silent`
- `excess_penalty` (optional):
  - Penalty datapoint (can be used in model design)

### FlixOpt Model Schema

The referenced model definition (`flixopt_model`) supports:

- `buses`
- `effects`
- `converters`
- `exchangers`
- `storages`
- `constraints_function` (optional)

See `FlixOptModel` in [flixopt_models.py](./flixopt_models.py) for detailed field definitions and validation rules.

### Custom Constraints

You can inject additional constraints into the optimization model.

- Configure `constraints_function` in the FlixOpt model.
- Value can be:
  - A Python file path (`*.py`), or
  - A Python module import path.
- The module must contain a function named `add_constraints`, like it is shown in [add_constraints.py](./add_constraints.py)

The function is loaded during component preparation and called before solving.

## Inputs

Input model: `FlixoptModelComponentInputData` (dynamic, `extra="allow"`).

That means input names are not hardcoded in the component config model. Required inputs are defined indirectly by your `flixopt_model`.

Typical input categories:

- Time-series inputs used in exchangers:
  - Example: heat demand, electricity demand, dynamic prices
- Scalar inputs for state/initialization:
  - Example: previous converter power, operation time, storage start SOC, storage capacity

Important requirements:

- All time series used by the optimization horizon must provide a valid `DatetimeIndex`.
- Input labels referenced in the model (for example in `input_label`, `previous_power`, `start_soc`) must exist in component inputs.

## Outputs

Output model: `FlixoptModelComponentOutputData` (dynamic, `extra="allow"`).

Generated outputs are mapped from optimization results:

- Storage state of charge:
  - `{storage_label}_soc`
- Converter thermal power:
  - `{converter_label}_thermal_power`
- CHP electrical power:
  - `{converter_label}_electrical_power`
- Exchanger flows:
  - `{exchanger_label}_input`
  - `{exchanger_label}_output`

Notes:

- For bidirectional substations, thermal output is exported as net value: forward flow minus reverse flow.
- The last optimization timestamp is dropped in exported time-series output to avoid incomplete end-step values.

## Minimal Configuration Example

This component block illustrates the relevant part in a service configuration:

```json
{
  "id": "flixopt_model_component",
  "type": "flixopt_model_component",
  "inputs": {
    "heat_demand": {
      "entity": "input_entity",
      "attribute": "heat_demand"
      },
    "electricity_price": {
      "entity": "input_entity",
      "attribute": "electricity_price"
      },
    "storage_level": {
      "entity": "input_entity",
      "attribute": "storage_level"
      }
  },
  "outputs": {
    "heater_thermal_power": {
      "entity": "output_entity",
      "attribute": "heater_power"
      }
  },
  "config": {
    "log_level": { "value": "debug" },
    "solver_settings": {
      "value": {
        "name": "HighsSolver",
        "mip_rel_gap": 0.01,
        "time_limit": 60
      }
    },
    "flixopt_model": {
      "value": "./flixopt_model_config.json"
    }
  }
}
```

The FlixOpt model must match the inputs and outputs; see the examples above.

## Example

A full working example is available in:

- [examples/09_flixopt](../../../examples/09_flixopt)

Relevant files:

- Example service configuration: [examples/09_flixopt/02_config_example.json](../../../examples/09_flixopt/02_config_example.json)
- Example FlixOpt model: [examples/09_flixopt/02_flixopt_model_config.json](../../../examples/09_flixopt/02_flixopt_model_config.json)
- Notebook to run the example: [examples/09_flixopt/run_example_optimisation.ipynb](../../../examples/09_flixopt/run_example_optimisation.ipynb)

## Troubleshooting

- `ValueError: Column ... not found in input DataFrame`:
  - A model input label references an input that is not present in provided timeseries.
- `Input time series must have a DatetimeIndex`:
  - Ensure all used timeseries are indexed by datetime.
- `Constraint function 'add_constraints' not found`:
  - Ensure the configured Python file/module exports a function named `add_constraints`.
- Solver errors:
  - Verify solver availability in your environment and the configured solver name.

## Developer Notes

- Core implementation: [flixopt_model_component.py](./flixopt_model_component.py)
- Config and runtime models: [flixopt_model_component_config.py](./flixopt_model_component_config.py)
- FlixOpt schema models: [flixopt_models.py](./flixopt_models.py)

The component inherits from `BasicComponent` and follows the same service integration lifecycle (`prepare_component()`, `calculate()`, output mapping) as other EnCoDaPy components.
