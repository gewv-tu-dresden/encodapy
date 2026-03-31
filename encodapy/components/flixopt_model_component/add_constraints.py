"""
Description: Example for the Function to add constraints to the FlixOpt \
    Optimization Model.
Author: Martin Altenburger
"""

import flixopt as fx # type: ignore[import-untyped]
from encodapy.components.flixopt_model_component.flixopt_models import FlixOptModel

def add_constraints(
    optimization: fx.Optimization,
    config: FlixOptModel | None = None,
) -> None:
    """
    Add new constraints to the optimization model.
    The function needs to be implemented for the specific use case

    Args:
        optimization (fx.Optimization): The optimization instance to which the constraints \
            will be added.
        config (FlixOptModel | None): The configuration object containing model parameters and \
            settings, which may be needed to determine how and which constraints to add.
    """
    _ = config
    # Example: Add constraints to the optimization model, only dummy variables!
    base_coords = optimization.model.get_coords()
    if base_coords is None:
        raise ValueError("Optimization model coordinates are not available.")

    example_variable_1 = optimization.model.add_variables(
        name="example_variable",
        coords=base_coords,
        binary=True,
    )
    example_variable_2 = optimization.model.add_variables(
        name="example_variable",
        coords=base_coords,
        binary=True,
    )
    optimization.model.add_constraints(
            example_variable_1 >= example_variable_2,
            name="example",
        )
