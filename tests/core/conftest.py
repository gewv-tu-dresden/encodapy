"""
Pytest fixtures for all core tests.

This module re-exports fixtures from basicservice/conftest.py to make them
available to all test files under tests/core/ and its subdirectories.
"""

# Import and re-export all fixtures from basicservice.conftest
from tests.core.basicservice.conftest import (
    mock_fiware_env,
    mock_file_env,
    mock_mqtt_env,
    create_service_without_init,
    create_service_for_config_tests,
    patch_prepare_basic_start,
    mock_basic_env,
    mock_fiware_entity,
    mock_file_entity,
    mock_mqtt_entity,
    mock_static_data_entity,
    mock_input_entity_fiware,
    mock_input_entity_file,
    mock_input_entity_mqtt,
    mock_config_all_interfaces,
    mock_config_no_interfaces,
    mock_config_only_fiware,
    basic_service,
    service_with_full_config,
    service_with_no_config,
    mock_data_transfer_model,
    mock_output_data_model,
    mock_input_data_model,
    shutdown_event,
    unset_shutdown_event,
)

# Also re-export all the mock env fixtures
__all__ = [
    'mock_fiware_env',
    'mock_file_env',
    'mock_mqtt_env',
    'create_service_without_init',
    'create_service_for_config_tests',
    'patch_prepare_basic_start',
    'mock_basic_env',
    'mock_fiware_entity',
    'mock_file_entity',
    'mock_mqtt_entity',
    'mock_static_data_entity',
    'mock_input_entity_fiware',
    'mock_input_entity_file',
    'mock_input_entity_mqtt',
    'mock_config_all_interfaces',
    'mock_config_no_interfaces',
    'mock_config_only_fiware',
    'basic_service',
    'service_with_full_config',
    'service_with_no_config',
    'mock_data_transfer_model',
    'mock_output_data_model',
    'mock_input_data_model',
    'shutdown_event',
    'unset_shutdown_event',
    'config_from_example_01',
]
