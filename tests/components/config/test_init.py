"""Test config init."""
from unittest.mock import patch

from openpeerpower.components import config
from openpeerpower.const import EVENT_COMPONENT_LOADED
from openpeerpower.setup import ATTR_COMPONENT, async_setup_component

from tests.common import mock_component, mock_coro


async def test_config_setup(opp, loop):
    """Test it sets up oppbian."""
    await async_setup_component(opp, "config", {})
    assert "config" in opp.config.components


async def test_load_on_demand_already_loaded(opp, aiohttp_client):
    """Test getting suites."""
    mock_component(opp, "zwave")

    with patch.object(config, "SECTIONS", []), patch.object(
        config, "ON_DEMAND", ["zwave"]
    ), patch("openpeerpower.components.config.zwave.async_setup") as stp:
        stp.return_value = mock_coro(True)

        await async_setup_component(opp, "config", {})

    await opp.async_block_till_done()
    assert stp.called


async def test_load_on_demand_on_load(opp, aiohttp_client):
    """Test getting suites."""
    with patch.object(config, "SECTIONS", []), patch.object(
        config, "ON_DEMAND", ["zwave"]
    ):
        await async_setup_component(opp, "config", {})

    assert "config.zwave" not in opp.config.components

    with patch("openpeerpower.components.config.zwave.async_setup") as stp:
        stp.return_value = mock_coro(True)
        opp.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "zwave"})
        await opp.async_block_till_done()

    assert stp.called
