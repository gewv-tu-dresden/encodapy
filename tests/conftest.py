# pylint: disable=unused-import
"""Central conftest.py – makes Docker fixtures available for all tests."""

import sys
import os

# Skip docker imports if running in CI or if SKIP_DOCKER_FIXTURES is set
# This prevents import conflicts with filip/pandas during test execution
skip_docker = os.environ.get('SKIP_DOCKER_FIXTURES', '0') == '1'

if not skip_docker:
    try:
        from tests.docker.conftest import (
            fiware_environment,
            fiware_cb_client,
            test_entity,
            fiware_envs,
        )
    except (ImportError, SystemExit):
        # Docker dependencies not available, skip docker fixtures
        pass
