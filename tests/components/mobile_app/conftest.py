"""Tests for mobile_app component."""
# pylint: disable=redefined-outer-name,unused-import
import pytest

from openpeerpower.components.mobile_app.const import DOMAIN
from openpeerpower.setup import async_setup_component

from .const import REGISTER, REGISTER_CLEARTEXT

from tests.common import mock_device_registry


@pytest.fixture
def registry(opp):
    """Return a configured device registry."""
    return mock_device_registry(opp)


@pytest.fixture
async def create_registrations(opp, authed_api_client):
    """Return two new registrations."""
    await async_setup_component(opp, DOMAIN, {DOMAIN: {}})

    enc_reg = await authed_api_client.post(
        "/api/mobile_app/registrations", json=REGISTER
    )

    assert enc_reg.status == 201
    enc_reg_json = await enc_reg.json()

    clear_reg = await authed_api_client.post(
        "/api/mobile_app/registrations", json=REGISTER_CLEARTEXT
    )

    assert clear_reg.status == 201
    clear_reg_json = await clear_reg.json()

    await opp.async_block_till_done()

    return (enc_reg_json, clear_reg_json)


@pytest.fixture
async def webhook_client(opp, authed_api_client, aiohttp_client):
    """mobile_app mock client."""
    # We pass in the authed_api_client server instance because
    # it is used inside create_registrations and just passing in
    # the app instance would cause the server to start twice,
    # which caused deprecation warnings to be printed.
    return await aiohttp_client(authed_api_client.server)


@pytest.fixture
async def authed_api_client(opp, opp_client):
    """Provide an authenticated client for mobile_app to use."""
    await async_setup_component(opp, DOMAIN, {DOMAIN: {}})
    await opp.async_block_till_done()
    return await opp_client()


@pytest.fixture(autouse=True)
async def setup_ws(opp):
    """Configure the websocket_api component."""
    assert await async_setup_component(opp, "websocket_api", {})
    await opp.async_block_till_done()
