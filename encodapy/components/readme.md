# Component Architecture of EnCoDaPy

## Structure of the Component Code

This module provides a structured way to define and manage components for use within the `EnCoDaPy` framework.

### Highlights

- Custom module for component definitions.
- Components are imported via `__init__.py` to enable simplified access.
- All components inherit from a base component with shared logic and configuration.
- Modular structure improves maintainability and reusability.

### Module Structure

- Component module: `encodapy.components`
- Base component: `encodapy.components.basic_component`
- Base configuration: `encodapy.components.basic_component_config`
- Individual component: `encodapy.components.$Component` (imported via `__init__.py`)

### Available Components

- ThermalStorage (`thermal_storage`): Thermal storage component to calculate the stored energy using temperature sensors.  
  An example can be found under: [`examples/06_thermal_storage_service`](../../examples/06_thermal_storage_service/)
- TwoPointController (`two_point_controller`): Two-Point-Controller component for the steering of the loading process of a thermal storage or other processes.  
  An example can be found under: [`examples/07_component_runner`](../../examples/07_component_runner/)

---

## Component Configuration

Component configuration must be customized per use case. It is recommended to validate the configuration during component initialization. This structure is formalized and can be validated using Pydantic.

### Shared Configuration Elements

Common configuration elements used across multiple components can be placed in:  
`encodapy.components.basic_component_config`

#### `ControllerComponentModel`

This is a model for configuring components that form part of the general configuration of a service.

#### `IOModell`

Root-Modell to describe the structur of the Inputs, Outputs and static data (`$INPUT_OR_OUTPUT_VARIABLE`) of a component as a dictionary of `IOAllocationModel`, like:

```json
{
  "inputs": {
    "INPUT_OR_OUTPUT_VARIABLE_1": "IOAllocationModel",
    "INPUT_OR_OUTPUT_VARIABLE_2": "IOAllocationModel"
  }
}

```

#### `IOAllocationModel`

Defines how inputs, outputs and static data of a component are mapped to specific entities and attributes.

The expected format for each input or output (`$INPUT_OR_OUTPUT_VARIABLE`) within the controller components (`controller_components`) configuration is:

```json
{
  "INPUT_OR_OUTPUT_VARIABLE": {
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

- an example is provided in [`examples/08_create_new_component`](../../examples/08_create_new_component)

### Infos for the New Component

- Inherits from `BasicComponent`
- Automatically gains:
  - Configuration parsing
  - Input discovery logic (to be triggered by the service)
  - A function to run the component and calculates all the outputs mentioned in the configuration.

- Each component needs the same structure in a module called `*.$new_component`:
  - `__init__.py`: can be empty
  - `new_component.py`: The Python module that initialises the class `NewComponent`.
  - `new_component_config.py`: The Python module containing all the necessary configurations.

  Make sure the names follow this convention if you want to use the component runner.

### Details to create a New Component

- When implementing a new component, begin by initializing the base class in `NewComponent`:

  ```python
  class NewComponent(BasicComponent):
    """
    Class for a new component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Add the necessary instance variables here
        self.example_variable:float = 1
        
        # Add the type declaration for the following variables so that autofill works properly
        self.config_data: NewComponentConfigData
        self.input_data: NewComponentInputData
        self.output_data: NewComponentOutputData

         # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )
  ```

  **Important**: The `component_id` must match a key in the provided configuration. If not, the component will raise a `ValueError` during initialization.

- The Configuration(`new_component_config.py`) needs as a minimum:
  - `NewComponentInputData(InputData)`: A definition of the input datapoints.
  
    You can add information about the default values in die Field-Information and also for units using a `Field` definition with the `json_schema_extra` key:

    ```python
    from pydantic import Field

    from encodapy.components.basic_component_config import (
      InputData
    )
    from encodapy.utils.datapoints import (
      DataPointGeneral,
      DataPointNumber
    )


    class NewComponentInputData(InputData):
        """
        Input model for the new component
        """

        input_value: DataPointGeneral = Field(
            ...,
            description="Input of the new component",
            json_schema_extra={"unit": "$unit_value"}
        )
        input_value_with_default: DataPointNumber = Field(
            DataPointNumber(value = 1),
            description="Input of the new component",
            json_schema_extra={"unit": "$unit_value"}
        )
    ```

    See https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage for information on the general usage of optional fields and default values.

    The value of the variable `"$unit_value"` must be a valid unit from the `encodapy.utils.units.DataUnits` such as `"CEL"` for °C. If possible, the unit will also be transformed.

  - `NewComponentOutputData(OutputData)`: A definition of the available output datapoints / results.

    ```python
    from pydantic import Field, Optional

    from encodapy.components.basic_component_config import OutputData
    from encodapy.utils.datapoints import DataPointGeneral

    class NewComponentOutputData(OutputData):
        """
        Output model for the new component
        """
  
        result: DataPointGeneral = Field(
            ...,
            description="Result of the new component",
            json_schema_extra={"unit": "$unit_value"}
        )
        optional_result: Optional[DataPointGeneral] = Field(
            ...,
            description="This is an optional result of the new component and does not need to be exported.",
            json_schema_extra={"unit": "$unit_value"}
        )
    ```

    **If you only want to use some of the possible results, you need to set them to  `Optional[DataPoint model]`** Therefore, there is no need to export them all in the service. If you add them all without 'Optional', you will get a 'ValidationError' if not all outputs are configured in the service configuration.

    As with the `NewComponentInputData`, you could also add information about the unit. If possible, the unit will also be transformed.

    The data points in this base model must be set in the `calculate()` function of each component so that the base component can handle them.
  - `NewComponentConfigData(ConfigData)`: A definition of the required static data to check during the initilisazion. It should look like this:

    ```python
    from encodapy.components.basic_component_config import ConfigData
    from encodapy.utils.datapoints import DataPointGeneral

    class NewComponentConfigData(ConfigData):
    """
    Model for the configuration data of the thermal storage service.
    """
    config_value: DataPointGeneral = Field(
        ...,
        description="Static value for the new component"
    )
    optional_config_value: Optional[DataPointGeneral] = Field(
        DataPointGeneral(value = 1),
        description="Optional static value for the new component"
    )
    ```

    You do not need this definition if you don't want to use static data.  
    You could add optional data that does not need to be set in the configuration. This should resemble the second field in the model.
  
  All datapoints need to have the type `DataPointGeneral` (see `encodapy.utils.datapoints`) or a specialized version of it. This type defines that the datapoints can have the following attributes:
  - a `value`
  - a `unit` (as `DataUnits`, e.g., `encodapy.utils.units.DataUnits`)
  - a `time` (as a datetime object)

  The following specialized versions restrict the type of `value` to ensure type consistency in calculations:
  - `DataPointNumber` for numbers (`float`/`int`)
  - `DataPointString` for text (`str`)
  - `DataPointDict` for dictionaries (`dict`)
  - `DataPointBool` for booleans (`bool`)
  - `DataPointMedium` for mediums (see `encodapy.utils.mediums`)

  You can define your own datatype by subclassing `DataPointGeneral` if you need a specialized version. This approach is also useful for defining default values when the value involves more than just a number.
  
- If the new component requires preparation before the first run, this should be added to the `prepare_component()` function.
- The basic component will handle the inputs, configuration data and outputs.
  - In order to use the autofil function in your IDE, you need to add a declaration of the types of `self.input_data`, `self.config_data` and `self.output_data`.
  - This basic function collects the data and enables you to query it using the InputData model, which is based on a Pydantic BaseModel: `self.input_data.input_value`. If you do not want to use the internal function `set_input_values(input_entities: list[InputDataEntityModel])`, you can add a custom function to handle the inputs.
  - The configuration data is available in the same way: `self.config_data.config_value`.
  - The new component requires a function `calculate()` to calculate the results, using the component's internal value storage and other background functions. These functions needs to set the `self.output_data = NewComponentOutputData(...)`.
  This data will be used by the basic component and the basic service/component runner service to create the output for the different interfaces.
- If the new component requires calibration, you should extend the function `calibrate()`. In the basic component, this function is only used to update static data.

### Using the New Component

- If you are using the structure for a new component, you can specify the module path in your project's configuration as the component type, as shown in the following example:

```json
{
  // ...
  "controller_components": [
      {
          "id": "example_controller",
          "type": "$your_project.$your_modules.$new_component",
          // ...
      }
    ]
  // ...
}
```
- Be careful: the module path must contain at least one dot. Otherwise, the framework will not recognise the component as an individual one.
