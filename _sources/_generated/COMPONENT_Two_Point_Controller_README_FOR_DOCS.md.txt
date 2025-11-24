# Two Point Controller

This component implements a simple two-point (on/off) controller with hysteresis.

## Functionality

- Compares a measured value to a setpoint and issues on/off commands.
- Applies hysteresis (deadband) to avoid rapid switching around the setpoint.
- Reads the latest control signal (optional) and can map configured enable/disable command values.

### Outputs
- `control_signal` (or configured output): the command/value sent by the controller when switching (enabled/disabled).

### Component Configuration

The component expects a Pydantic configuration model (see `two_point_controller_config.py`). Typical configuration options:
- `setpoint`: numeric value or datapoint reference for the desired target.
- `hysteresis`: numeric deadband around the setpoint.
- `command_enabled` / `command_disabled`: values to send when the controller turns on/off.
- Optional mappings for inputs and outputs (datapoints or connections).

Configuration values can be provided as static data or as datapoints in the service config.

## Inputs

- `current_value`: measured value used for control.
- `latest_control_signal`: (optional) last known output value from the actuator or controller.

## Example

An example using this component together with a thermal storage is available in [examples/07_component_runner/config.json](https://github.com/gewv-tu-dresden/encodapy/blob/main/examples/07_component_runner/config.json) (see the `two_point_controller` entry).
