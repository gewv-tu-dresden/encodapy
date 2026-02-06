# Example for Optimization

- We use the [flixOpt](https://flixopt.github.io/flixopt/latest/) Python framework to model, optimise and analyse complex energy systems.
- The aim is to use optimisation to create a schedule for a decentralised component.
- The example is still being built.

## Example from FlixOpt
- [flixopt_example_component](./flixopt_example_component/): Component based on https://flixopt.github.io/flixopt/latest/examples/02-Complex%20Example/
- [inputs_flixopt.csv](./inputs_flixopt.csv): Example input data / only local example

- [01_config_example.json](./01_config_example.json): Configuration for this example with local input file
- [01_run_example_optimisation.ipynb](./01_run_example_optimisation.ipynb): Notebook to run this example

## FlixOpt Model for Energy Management

- [flixopt_model_component](./flixopt_model_component): Component to create a simple flixopt model for energy management
- [02_flixopt_model_config.json](./02_flixopt_model_config.json): Configuration for the flixopt model --> there is an adaptation necessary for a better integration in the encodapy configuration
- [02_config_example.json](./02_config_example.json): Configuration for this example with local input file
- [static_data_flixopt.json](./static_data_flixopt.json): Input data for test purposes

## Basic Files

- [run_example_optimisation.ipynb](./run_example_optimisation.ipynb): Notebook to run this example, adjust the example by `.env`