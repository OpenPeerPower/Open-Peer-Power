"""The tests for the Demo component."""
import json
import os

import pytest

from openpeerpower.components import demo
from openpeerpower.components.device_tracker.legacy import YAML_DEVICES
from openpeerpower.helpers.json import JSONEncoder
from openpeerpower.setup import async_setup_component


@pytest.fixture(autouse=True)
def mock_history(opp):
    """Mock history component loaded."""
    opp.config.components.add("history")


@pytest.fixture(autouse=True)
def demo_cleanup(opp):
    """Clean up device tracker demo file."""
    yield
    try:
        os.remove(opp.config.path(YAML_DEVICES))
    except FileNotFoundError:
        pass


async def test_setting_up_demo(opp):
    """Test if we can set up the demo and dump it to JSON."""
    assert await async_setup_component(opp, demo.DOMAIN, {"demo": {}})
    await opp.async_start()

    # This is done to make sure entity components don't accidentally store
    # non-JSON-serializable data in the state machine.
    try:
        json.dumps(opp.states.async_all(), cls=JSONEncoder)
    except Exception:
        pytest.fail(
            "Unable to convert all demo entities to JSON. "
            "Wrong data in state machine!"
        )
