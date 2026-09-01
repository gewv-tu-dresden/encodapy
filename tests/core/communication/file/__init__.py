"""
Tests for FILE communication interfaces in EnCoDaPy.

This package contains unit and integration tests for the FILE communication
module, covering:
- Connection management and configuration
- Data query and retrieval from local files (CSV, JSON)
- Data sending and file writing operations
- Static data loading from files
- Time parsing and handling
- Unit conversion and adjustment for file compatibility
- Integration tests with Docker containers (if applicable)

Test Organization:
- Unit Tests (fast, no external dependencies):
  - test_file_connection.py: Connection setup and configuration
  - test_file_data_query.py: Data retrieval logic from CSV and JSON files
  - test_file_data_send.py: Data sending logic and file writing operations
  - test_file_time_parsing.py: Time parsing and date handling

- Integration Tests (require Docker containers, if applicable):
  - integration/test_file_connection_integration.py: End-to-end tests

All unit tests use pytest framework with mocked dependencies.
Integration tests require Docker containers and use testcontainers.

Shared fixtures for unit tests are in conftest.py.
Shared fixtures for integration tests are in integration/conftest.py.
"""
