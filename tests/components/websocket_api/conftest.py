"""Fixtures for websocket tests."""
import pytest

from openpeerpower.components.websocket_api.auth import TYPE_AUTH_REQUIRED
from openpeerpower.components.websocket_api.http import URL
from openpeerpower.setup import async_setup_component


@pytest.fixture
def websocket_client(opp, opp_ws_client, opp_access_token):
    """Create a websocket client."""
    return opp.loop.run_until_complete(opp_ws_client(opp, opp_access_token))


@pytest.fixture
def no_auth_websocket_client(opp, loop, aiohttp_client):
    """Websocket connection that requires authentication."""
    assert loop.run_until_complete(async_setup_component(opp, "websocket_api", {}))

    client = loop.run_until_complete(aiohttp_client(opp.http.app))
    ws = loop.run_until_complete(client.ws_connect(URL))

    auth_ok = loop.run_until_complete(ws.receive_json())
    assert auth_ok["type"] == TYPE_AUTH_REQUIRED

    yield ws

    if not ws.closed:
        loop.run_until_complete(ws.close())
