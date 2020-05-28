# pylint: disable=redefined-outer-name
"""Tests for the Daikin config flow."""
import asyncio
from unittest.mock import patch

import pytest

from openpeerpower import data_entry_flow
from openpeerpower.components.daikin import config_flow
from openpeerpower.components.daikin.const import KEY_IP, KEY_MAC
from openpeerpower.const import CONF_HOST

from tests.common import MockConfigEntry

MAC = "AABBCCDDEEFF"
HOST = "127.0.0.1"


def init_config_flow(opp):
    """Init a configuration flow."""
    flow = config_flow.FlowHandler()
    flow.opp = opp
    return flow


@pytest.fixture
def mock_daikin():
    """Mock pydaikin."""

    async def mock_daikin_init():
        """Mock the init function in pydaikin."""
        pass

    with patch("openpeerpower.components.daikin.config_flow.Appliance") as Appliance:
        Appliance().values.get.return_value = "AABBCCDDEEFF"
        Appliance().init = mock_daikin_init
        yield Appliance


async def test_user(opp, mock_daikin):
    """Test user config."""
    flow = init_config_flow(opp)

    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await flow.async_step_user({CONF_HOST: HOST})
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][KEY_MAC] == MAC


async def test_abort_if_already_setup(opp, mock_daikin):
    """Test we abort if Daikin is already setup."""
    flow = init_config_flow(opp)
    MockConfigEntry(domain="daikin", data={KEY_MAC: MAC}).add_to_opp(opp)

    result = await flow.async_step_user({CONF_HOST: HOST})
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_import(opp, mock_daikin):
    """Test import step."""
    flow = init_config_flow(opp)

    result = await flow.async_step_import({})
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    result = await flow.async_step_import({CONF_HOST: HOST})
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][KEY_MAC] == MAC


async def test_discovery(opp, mock_daikin):
    """Test discovery step."""
    flow = init_config_flow(opp)

    result = await flow.async_step_discovery({KEY_IP: HOST, KEY_MAC: MAC})
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"][CONF_HOST] == HOST
    assert result["data"][KEY_MAC] == MAC


@pytest.mark.parametrize(
    "s_effect,reason",
    [(asyncio.TimeoutError, "device_timeout"), (Exception, "device_fail")],
)
async def test_device_abort(opp, mock_daikin, s_effect, reason):
    """Test device abort."""
    flow = init_config_flow(opp)
    mock_daikin.side_effect = s_effect

    result = await flow.async_step_user({CONF_HOST: HOST})
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == reason
