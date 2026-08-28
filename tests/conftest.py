# pylint: disable=unused-import
"""Central conftest.py – makes Docker fixtures available for all tests."""
from tests.docker.conftest import (
    fiware_environment,
    fiware_cb_client,
    test_entity,
    fiware_envs,
)
