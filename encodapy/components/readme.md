# Component Architecture of `encodapy`

## Structure of the Component Code

This module provides a structured way to define and manage components for use within the `encodapy` framework.

### Highlights

- Custom module for component definitions.
- Components are imported via `__init__.py` to enable simplified access.
- All components inherit from a base component with shared logic and configuration.
- Modular structure improves maintainability and reusability.

### Module Structure

- Component module: `encodapy.components`
- Base component: `encodapy.components.basic_component`
- Base configuration: `encodapy.components.components_basic_config`
- Individual component: `encodapy.components.$Component` (imported via `__init__.py`)

### Available Components

- `ThermalStorage`: Thermal storage component to calculate the stored energy using temperature sensors.  
  An example can be found under:  
  [`examples/06_thermal_storage_service`](../../examples/06_thermal_storage_service/)

---

## Component Configuration

Component configuration must be customized per use case. It is recommended to validate the configuration during component initialization. This structure is formalized and can be validated using Pydantic.

### Shared Configuration Elements

Common configuration elements used across multiple components can be placed in:  
`encodapy.components.components_basic_config`

#### `ControllerComponentModel`
This is a model for configuring components that form part of the general configuration of a service.

#### `IOModell`
Root-Modell to describe the structur of the Inputs, Outputs and static data (`$INPUT_OR_OUTPUT_VARIABLE`) of a component as a dictionary of `IOAllocationModel`, like:
```json

  "inputs": {
    "$INPUT_OR_OUTPUT_VARIABLE_1": IOAllocationModel,
    "$INPUT_OR_OUTPUT_VARIABLE_2": IOAllocationModel
  }

```

#### `IOAllocationModel`

Defines how inputs, outputs and static data of a component are mapped to specific entities and attributes.

The expected format for each input or output (`$INPUT_OR_OUTPUT_VARIABLE`) within the controller components (`controller_components`) configuration is:

```json
{
  "$INPUT_OR_OUTPUT_VARIABLE": {
    "entity": "entity_id",
    "attribute": "attribute_id"
  }
}
```
#### `ControllerComponentStaticData`
A model for storing the static data of a component as a dict of `ControllerComponentStaticDataAttribute` in a Pydantic root model.

#### `ControllerComponentStaticDataAttribute`
Model for the static data attributes of the controller component, is part if the `ControllerComponentStaticData`-Model.


### Example Configuration

An example of how a Pydantic model can be used to validate the configuration of a component is available at:  
[`encodapy/components/thermal_storage/thermal_storage_config.py`](./thermal_storage/thermal_storage_config.py)

---

## Implementing a New Component

### Each New Component

- Inherits from `BasicComponent`
- Automatically gains:
  - Configuration parsing
  - Input discovery logic (to be triggered by the service)

### Example Constructor

When implementing a new component, begin by initializing the base class:

```python
def __init__(self,
             config: Union[ControllerComponentModel, list[ControllerComponentModel]],
             component_id: str
             ) -> None:

    super().__init__(config=config,
                     component_id=component_id)

    # Component-specific initialization logic
```

**Important**: The `component_id` must match a key in the provided configuration.  
If not, the component will raise a `ValueError` during initialization.