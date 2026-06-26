"""
Description: Example for the Function to add constraints to the FlixOpt \
    Optimization Model.
Author: Martin Altenburger
"""

import flixopt as fx # type: ignore[import-untyped]
from encodapy.components.flixopt_model_component.flixopt_models import FlixOptModel


def _add_piecewise_example() -> list[fx.LinearConverter]:
    """
    Example for adding a piecewise linear function to the optimization model as an element.

    See https://flixopt.github.io/flixopt/latest/notebooks/06b-piecewise-conversion/
    """

    piecewise_efficiency = fx.PiecewiseConversion(
        {
            'gas': fx.Piecewise(
                [
                    fx.Piece(start=78, end=132),  # Part load
                    fx.Piece(start=132, end=179),  # Mid load
                    fx.Piece(start=179, end=250),  # Full load
                ]
            ),
            'electricity': fx.Piecewise(
                [
                    fx.Piece(start=25, end=50),  # 32% -> 38% efficiency
                    fx.Piece(start=50, end=75),  # 38% -> 42% efficiency
                    fx.Piece(start=75, end=100),  # 42% -> 40% efficiency
                ]
            ),
        }
    )

    converter = fx.LinearConverter(
        'GasEngine',
        # this flows needs to exists in the model, define them in the configuration
        inputs=[fx.Flow('gas', bus='gas')],
        outputs=[fx.Flow('electricity', bus='electricity')],
        piecewise_conversion=piecewise_efficiency,
    )

    return [converter]

def add_elements(
    config: FlixOptModel | None = None,
) -> list[fx.elements.Element]:
    """
    Add new elements to the flow system of the optimization model.
    
    The function needs to be implemented for the specific use case \
        and need to return a list of flixopt components which should be added to the model.

    Args:
        config (FlixOptModel | None): The configuration object containing model parameters and \
            settings, which may be needed to determine how and which constraints to add.
    """
    _ = config # if you want to use the config

    fx_elements: list[fx.elements.Element] = []

    # as example, add a piecewise linear converter to the model
    fx_elements.extend(_add_piecewise_example())

    return fx_elements
