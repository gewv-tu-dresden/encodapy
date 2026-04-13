# FlixoptModelComponent Tests

This folder contains the tests for the FlixoptModelComponent.
The goal is to cover data preparation, model assembly, optimization runtime,
and output mapping in a maintainable way.

## Structure

- unit/test_flixopt_model_component_helpers.py: helper methods, input handling,
  logging forwarding, and simple control-flow checks.
- unit/test_flixopt_model_component_runtime.py: runtime behavior, converter
  dispatch, and optimization success and failure paths.
- unit/test_flixopt_model_component_branches.py: targeted branch and edge-case
  tests for defensive and hard-to-reach code paths.
- integration/test_flixopt_model_component_output_mapping.py:
  integration-style checks for result export and domain output mapping.

Note: The legacy bidirectional output mapping test is intentionally kept in
tests/components/test_flixopt_model_component_bidirectional_output.py so that
existing references and backward compatibility remain intact.

## Running the tests

Run only this component suite:

```bash
poetry run pytest tests/components/flixopt_model_component -q
```

Run the component suite plus the legacy bidirectional test:

```bash
poetry run pytest tests/components/flixopt_model_component tests/components/test_flixopt_model_component_bidirectional_output.py -q
```

Run the component suite with coverage for the target module:

```bash
poetry run pytest tests/components/flixopt_model_component tests/components/test_flixopt_model_component_bidirectional_output.py --cov=encodapy.components.flixopt_model_component.flixopt_model_component --cov-report=term-missing -q
```

## Test Function Overview

### unit/test_flixopt_model_component_helpers.py

- test_get_input_value_returns_literal_numbers: Returns literal float and int values unchanged.
- test_get_input_value_returns_ndarray_for_series: Converts a pandas Series input to a NumPy array.
- test_get_input_arrays_returns_column_values: Reads the prepared input column values.
- test_prepare_input_data_merges_series_and_strips_timezone: Merges time series inputs and removes timezone information.
- test_load_helper_functions_loads_python_module: Loads a helper function from a Python file.
- test_prepare_component_rejects_invalid_model_payload: Rejects an invalid flixopt_model payload.
- test_min_uptime_profile_is_reduced_for_carry_over_runtime: Reduces min_uptime when a converter has already been running.
- test_get_storages_clips_initial_soc_to_bounds: Clamps the initial state of charge to the configured bounds.
- test_get_sinks_and_sources_builds_bidirectional_source_and_sink: Builds the bidirectional sink and source structure.
- test_loguru_forward_handler_handles_format_errors: Exercises the error path of the Loguru forwarding handler.
- test_configure_linopy_logging_is_idempotent: Verifies that the linopy logging setup is idempotent.
- test_load_helper_functions_raises_for_missing_symbol: Raises an error when the requested symbol is missing.
- test_get_input_value_raises_for_none_when_not_allowed: Rejects None when none_allowed is False.
- test_prepare_input_data_returns_when_index_not_datetime: Skips DataFrame creation for a non-datetime index.
- test_prepare_flixopt_flow_system_raises_without_datetime_index: Raises when the datetime input index is not prepared.
- test_calculate_skips_output_preparation_when_optimization_fails: Skips output preparation if optimization does not return results.
- test_calculate_runs_output_preparation_on_success: Runs output preparation after a successful optimization.

### unit/test_flixopt_model_component_runtime.py

- test_prepare_component_loads_model_from_dict: Loads the model correctly from a dictionary.
- test_get_converters_skips_invalid_chp_entry: Skips an invalid CHP entry during converter creation.
- test_add_bidirectional_constraints_raises_when_coords_missing: Raises when model coordinates are unavailable.
- test_run_optimization_returns_none_on_modeling_error: Returns None when modeling fails.
- test_run_optimization_returns_none_on_solver_runtime_error: Returns None when the solver raises a runtime error.
- test_run_optimization_returns_results_on_success: Returns the optimization results on success.
- test_get_converters_dispatches_all_supported_types: Dispatches all supported converter types.

### unit/test_flixopt_model_component_branches.py

- test_init_sets_default_members: Verifies constructor defaults.
- test_prepare_component_file_not_found_raises: Raises for a missing model file.
- test_prepare_component_raises_validation_error_for_invalid_model: Raises a validation error for an incomplete model.
- test_prepare_component_reaches_non_dict_non_path_value_branch: Covers the defensive branch for an invalid value type.
- test_prepare_component_loads_constraint_and_element_helpers: Loads optional constraint and manual element helpers.
- test_load_helper_functions_import_errors: Exercises import errors for missing spec or loader.
- test_load_helper_functions_returns_none_for_empty_symbol: Returns None for an empty symbol name.
- test_load_helper_functions_raises_for_non_function_symbol: Rejects symbols that are not callable functions.
- test_get_input_arrays_raises_for_missing_data_and_column: Raises when the input DataFrame or column is missing.
- test_get_input_value_unknown_key_and_invalid_none_allowed: Raises for an unknown key or invalid value content.
- test_get_input_value_returns_none_if_allowed: Accepts None when it is allowed.
- test_get_input_value_raises_if_input_data_missing: Raises when input_data has not been prepared.
- test_get_input_value_raises_for_non_numeric_without_none_allowed: Raises for non-numeric input values.
- test_prepare_input_data_uses_default_hour_for_non_inferable_freq: Covers the fallback path for an uninferrable frequency.
- test_prepare_flixopt_flow_system_builds_elements: Builds a flow system with buses and effects.
- test_add_chp_converter_raises_for_wrong_type: Rejects a converter that does not match the CHP builder type.
- test_converter_builder_methods_return_constructed_objects: Verifies the converter builder helpers return the expected objects.
- test_add_bidirectional_substation_converter_rejects_non_positive_efficiency: Rejects a bidirectional substation with non-positive efficiency.
- test_add_bidirectional_substation_converter_builds_forward_and_reverse: Builds forward and reverse converters for the bidirectional case.
- test_get_converters_handles_valid_chp_branch: Covers the CHP branch in converter dispatch.
- test_add_bidirectional_substation_constraints_adds_binary_gates: Adds binary gates for bidirectional flows.
- test_get_flow_effects_and_information_return_empty_on_invalid_direction: Covers the defensive return path for an invalid direction.
- test_get_sinks_and_sources_skips_unknown_direction: Skips exchangers with an unknown direction.
- test_get_sinks_and_sources_handles_source_direction: Builds a source for SOURCE direction.
- test_loguru_forward_handler_success_path: Exercises the success path of log forwarding.
- test_run_optimization_calls_constraint_function: Invokes the optional constraint function.
- test_run_optimization_manual_elements_invalid_type_raises: Rejects invalid manual elements.
- test_run_optimization_returns_none_on_file_not_found: Returns None when the solver file cannot be found.
- test_export_results_as_timeseries_raises_when_input_missing: Raises when no input time series are prepared.
- test_export_results_as_timeseries_handles_scalar_data_var: Ignores scalar data variables during export.
- test_prepare_output_data_maps_chp_and_exchanger_io: Maps CHP and exchanger inputs and outputs.

### integration/test_flixopt_model_component_output_mapping.py

- test_prepare_output_data_uses_forward_minus_reverse: Computes net power for bidirectional mapping.
- test_export_results_as_timeseries_removes_last_row_and_preserves_index_tz: Removes the final row and preserves the timezone.
- test_prepare_output_data_maps_storage_and_converter_outputs: Maps storage SOC, thermal power, and status outputs.

## Maintenance Notes

- Add new tests to the appropriate file group: helpers, runtime, branches, or integration.
- Keep test names in the form test_<behavior>_<expectation>.
- Update this overview when new special cases are added.
