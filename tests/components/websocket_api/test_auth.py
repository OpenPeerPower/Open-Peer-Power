"""Test auth of websocket API."""
from unittest.mock import patch

from openpeerpower.components.websocket_api.auth import (
    TYPE_AUTH,
    TYPE_AUTH_INVALID,
    TYPE_AUTH_OK,
    TYPE_AUTH_REQUIRED,
)
from openpeerpower.components.websocket_api.const import (
    SIGNAL_WEBSOCKET_CONNECTED,
    SIGNAL_WEBSOCKET_DISCONNECTED,
    URL,
)
from openpeerpower.setup import async_setup_component

from tests.common import mock_coro


async def test_auth_events(
    opp, no_auth_websocket_client, legacy_auth, opp_access_token
):
    """Test authenticating."""
    connected_evt = []
    opp.helpers.dispatcher.async_dispatcher_connect(
        SIGNAL_WEBSOCKET_CONNECTED, lambda: connected_evt.append(1)
    )
    disconnected_evt = []
    opp.helpers.dispatcher.async_dispatcher_connect(
        SIGNAL_WEBSOCKET_DISCONNECTED, lambda: disconnected_evt.append(1)
    )

    await test_auth_active_with_token(opp, no_auth_websocket_client, opp_access_token)

    assert len(connected_evt) == 1
    assert not disconnected_evt

    await no_auth_websocket_client.close()
    await opp.async_block_till_done()

    assert len(disconnected_evt) == 1


async def test_auth_via_msg_incorrect_pass(no_auth_websocket_client):
    """Test authenticating."""
    with patch(
        "openpeerpower.components.websocket_api.auth.process_wrong_login",
        return_value=mock_coro(),
    ) as mock_process_wrong_login:
        await no_auth_websocket_client.send_json(
            {"type": TYPE_AUTH, "api_password": "wrong"}
        )

        msg = await no_auth_websocket_client.receive_json()

    assert mock_process_wrong_login.called
    assert msg["type"] == TYPE_AUTH_INVALID
    assert msg["message"] == "Invalid access token or password"


async def test_auth_events_incorrect_pass(opp, no_auth_websocket_client):
    """Test authenticating."""
    connected_evt = []
    opp.helpers.dispatcher.async_dispatcher_connect(
        SIGNAL_WEBSOCKET_CONNECTED, lambda: connected_evt.append(1)
    )
    disconnected_evt = []
    opp.helpers.dispatcher.async_dispatcher_connect(
        SIGNAL_WEBSOCKET_DISCONNECTED, lambda: disconnected_evt.append(1)
    )

    await test_auth_via_msg_incorrect_pass(no_auth_websocket_client)

    assert not connected_evt
    assert not disconnected_evt

    await no_auth_websocket_client.close()
    await opp.async_block_till_done()

    assert not connected_evt
    assert not disconnected_evt


async def test_pre_auth_only_auth_allowed(no_auth_websocket_client):
    """Verify that before authentication, only auth messages are allowed."""
    await no_auth_websocket_client.send_json(
        {
            "type": "call_service",
            "domain": "domain_test",
            "service": "test_service",
            "service_data": {"hello": "world"},
        }
    )

    msg = await no_auth_websocket_client.receive_json()

    assert msg["type"] == TYPE_AUTH_INVALID
    assert msg["message"].startswith("Auth message incorrectly formatted")


async def test_auth_active_with_token(opp, no_auth_websocket_client, opp_access_token):
    """Test authenticating with a token."""
    assert await async_setup_component(opp, "websocket_api", {})

    await no_auth_websocket_client.send_json(
        {"type": TYPE_AUTH, "access_token": opp_access_token}
    )

    auth_msg = await no_auth_websocket_client.receive_json()
    assert auth_msg["type"] == TYPE_AUTH_OK


async def test_auth_active_user_inactive(opp, aiohttp_client, opp_access_token):
    """Test authenticating with a token."""
    refresh_token = await opp.auth.async_validate_access_token(opp_access_token)
    refresh_token.user.is_active = False
    assert await async_setup_component(opp, "websocket_api", {})

    client = await aiohttp_client(opp.http.app)

    async with client.ws_connect(URL) as ws:
        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_REQUIRED

        await ws.send_json({"type": TYPE_AUTH, "access_token": opp_access_token})

        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_INVALID


async def test_auth_active_with_password_not_allow(opp, aiohttp_client):
    """Test authenticating with a token."""
    assert await async_setup_component(opp, "websocket_api", {})

    client = await aiohttp_client(opp.http.app)

    async with client.ws_connect(URL) as ws:
        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_REQUIRED

        await ws.send_json({"type": TYPE_AUTH, "api_password": "some-password"})

        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_INVALID


async def test_auth_legacy_support_with_password(opp, aiohttp_client, legacy_auth):
    """Test authenticating with a token."""
    assert await async_setup_component(opp, "websocket_api", {})

    client = await aiohttp_client(opp.http.app)

    async with client.ws_connect(URL) as ws:
        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_REQUIRED

        await ws.send_json({"type": TYPE_AUTH, "api_password": "some-password"})

        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_INVALID


async def test_auth_with_invalid_token(opp, aiohttp_client):
    """Test authenticating with a token."""
    assert await async_setup_component(opp, "websocket_api", {})

    client = await aiohttp_client(opp.http.app)

    async with client.ws_connect(URL) as ws:
        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_REQUIRED

        await ws.send_json({"type": TYPE_AUTH, "access_token": "incorrect"})

        auth_msg = await ws.receive_json()
        assert auth_msg["type"] == TYPE_AUTH_INVALID