"""The tests for the oppio component."""
import asyncio
from unittest.mock import patch

import pytest


async def test_forward_request(oppio_client, aioclient_mock):
    """Test fetching normal path."""
    aioclient_mock.post("http://127.0.0.1/beer", text="response")

    resp = await oppio_client.post("/api/oppio/beer")

    # Check we got right response
    assert resp.status == 200
    body = await resp.text()
    assert body == "response"

    # Check we forwarded command
    assert len(aioclient_mock.mock_calls) == 1


@pytest.mark.parametrize(
    "build_type", ["supervisor/info", "openpeerpower/update", "host/info"]
)
async def test_auth_required_forward_request(oppio_noauth_client, build_type):
    """Test auth required for normal request."""
    resp = await oppio_noauth_client.post("/api/oppio/{}".format(build_type))

    # Check we got right response
    assert resp.status == 401


@pytest.mark.parametrize(
    "build_type",
    [
        "app/index.html",
        "app/oppio-app.html",
        "app/index.html",
        "app/oppio-app.html",
        "app/some-chunk.js",
        "app/app.js",
    ],
)
async def test_forward_request_no_auth_for_panel(
    oppio_client, build_type, aioclient_mock
):
    """Test no auth needed for ."""
    aioclient_mock.get("http://127.0.0.1/{}".format(build_type), text="response")

    resp = await oppio_client.get("/api/oppio/{}".format(build_type))

    # Check we got right response
    assert resp.status == 200
    body = await resp.text()
    assert body == "response"

    # Check we forwarded command
    assert len(aioclient_mock.mock_calls) == 1


async def test_forward_request_no_auth_for_logo(oppio_client, aioclient_mock):
    """Test no auth needed for logo."""
    aioclient_mock.get("http://127.0.0.1/addons/bl_b392/logo", text="response")

    resp = await oppio_client.get("/api/oppio/addons/bl_b392/logo")

    # Check we got right response
    assert resp.status == 200
    body = await resp.text()
    assert body == "response"

    # Check we forwarded command
    assert len(aioclient_mock.mock_calls) == 1


async def test_forward_request_no_auth_for_icon(oppio_client, aioclient_mock):
    """Test no auth needed for icon."""
    aioclient_mock.get("http://127.0.0.1/addons/bl_b392/icon", text="response")

    resp = await oppio_client.get("/api/oppio/addons/bl_b392/icon")

    # Check we got right response
    assert resp.status == 200
    body = await resp.text()
    assert body == "response"

    # Check we forwarded command
    assert len(aioclient_mock.mock_calls) == 1


async def test_forward_log_request(oppio_client, aioclient_mock):
    """Test fetching normal log path doesn't remove ANSI color escape codes."""
    aioclient_mock.get("http://127.0.0.1/beer/logs", text="\033[32mresponse\033[0m")

    resp = await oppio_client.get("/api/oppio/beer/logs")

    # Check we got right response
    assert resp.status == 200
    body = await resp.text()
    assert body == "\033[32mresponse\033[0m"

    # Check we forwarded command
    assert len(aioclient_mock.mock_calls) == 1


async def test_bad_gateway_when_cannot_find_supervisor(oppio_client):
    """Test we get a bad gateway error if we can't find supervisor."""
    with patch(
        "openpeerpower.components.oppio.http.async_timeout.timeout",
        side_effect=asyncio.TimeoutError,
    ):
        resp = await oppio_client.get("/api/oppio/addons/test/info")
    assert resp.status == 502


async def test_forwarding_user_info(oppio_client, opp_admin_user, aioclient_mock):
    """Test that we forward user info correctly."""
    aioclient_mock.get("http://127.0.0.1/hello")

    resp = await oppio_client.get("/api/oppio/hello")

    # Check we got right response
    assert resp.status == 200

    assert len(aioclient_mock.mock_calls) == 1

    req_headers = aioclient_mock.mock_calls[0][-1]
    req_headers["X-Opp-User-ID"] == opp_admin_user.id
    req_headers["X-Opp-Is-Admin"] == "1"
