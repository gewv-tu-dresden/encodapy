"""
Pytest fixtures for service tests.

This conftest prevents the loading of global fixtures that might cause conflicts.
"""

import os

# Prevent loading of global conftest that imports Docker fixtures
# when running service tests
os.environ['SKIP_DOCKER_FIXTURES'] = '1'
