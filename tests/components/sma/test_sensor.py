"""SMA sensor tests."""
import logging

from openpeerpower.components.sensor import DOMAIN
from openpeerpower.setup import async_setup_component

from tests.common import assert_setup_component

_LOGGER = logging.getLogger(__name__)
BASE_CFG = {
    "platform": "sma",
    "host": "1.1.1.1",
    "password": "",
    "custom": {"my_sensor": {"key": "1234567890123", "unit": "V"}},
}


async def test_sma_config(opp):
    """Test new config."""
    sensors = ["current_consumption"]

    with assert_setup_component(1):
        assert await async_setup_component(
            opp, DOMAIN, {DOMAIN: dict(BASE_CFG, sensors=sensors)}
        )

    state = opp.states.get("sensor.current_consumption")
    assert state
    assert "unit_of_measurement" in state.attributes
    assert "current_consumption" not in state.attributes

    state = opp.states.get("sensor.my_sensor")
    assert state
