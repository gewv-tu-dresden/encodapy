"""
Tests for FIWARE communication interfaces in EnCoDaPy.

This package contains unit and integration tests for the FIWARE communication
module, covering:
- Connection management and configuration
- Data query and retrieval from FIWARE Context Broker
- Data sending and entity updates to FIWARE
- Unit conversion and adjustment for FIWARE compatibility
- Integration tests with Docker containers

Test Organization:
- test_fiware_connection.py: Unit tests for connection setup and configuration
- test_fiware_connection_integration.py: Integration tests with Docker containers
- test_fiware_data_query.py: Unit tests for data retrieval logic
- test_fiware_data_send.py: Unit tests for data sending logic including unit adjustment

All tests use pytest framework and mock external dependencies where appropriate.
"""
