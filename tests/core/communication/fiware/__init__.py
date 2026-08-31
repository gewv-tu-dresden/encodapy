"""
Tests for FIWARE communication interfaces in EnCoDaPy.

This package contains unit and integration tests for the FIWARE communication
module, covering:
- Connection management and configuration
- Data query and retrieval from FIWARE Context Broker
- Data sending and entity updates to FIWARE
- Unit conversion and adjustment for FIWARE compatibility
- Time calculation utilities
- Integration tests with Docker containers

Test Organization:
- Unit Tests (fast, no external dependencies):
  - test_fiware_connection.py: Connection setup and configuration
  - test_fiware_data_query.py: Data retrieval logic and metadata extraction
  - test_fiware_data_send.py: Data sending logic and unit adjustment
  - test_fiware_time_calculation.py: Time range and date calculation

- Integration Tests (require Docker containers):
  - integration/test_fiware_connection_integration.py: End-to-end tests

All unit tests use pytest framework with mocked dependencies.
Integration tests require Docker containers and use testcontainers.

Shared fixtures for unit tests are in conftest.py.
Shared fixtures for integration tests are in integration/conftest.py.
"""
