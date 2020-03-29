"""The tests for the Open Peer Power HTTP component."""
from datetime import timedelta
from ipaddress import ip_network
from unittest.mock import patch

from aiohttp import BasicAuth, web
from aiohttp.web_exceptions import HTTPUnauthorized
import pytest

from openpeerpower.auth.providers import trusted_networks
from openpeerpower.components.http.auth import async_sign_path, setup_auth
from openpeerpower.components.http.const import KEY_AUTHENTICATED
from openpeerpower.components.http.real_ip import setup_real_ip
from openpeerpower.setup import async_setup_component

from . import HTTP_HEADER_HA_AUTH, mock_real_ip

API_PASSWORD = "test-password"

# Don't add 127.0.0.1/::1 as trusted, as it may interfere with other test cases
TRUSTED_NETWORKS = [
    ip_network("192.0.2.0/24"),
    ip_network("2001:DB8:ABCD::/48"),
    ip_network("100.64.0.1"),
    ip_network("FD01:DB8::1"),
]
TRUSTED_ADDRESSES = ["100.64.0.1", "192.0.2.100", "FD01:DB8::1", "2001:DB8:ABCD::1"]
UNTRUSTED_ADDRESSES = ["198.51.100.1", "2001:DB8:FA1::1", "127.0.0.1", "::1"]


async def mock_handler(request):
    """Return if request was authenticated."""
    if not request[KEY_AUTHENTICATED]:
        raise HTTPUnauthorized

    user = request.get("opp_user")
    user_id = user.id if user else None

    return web.json_response(status=200, data={"user_id": user_id})


async def get_legacy_user(auth):
    """Get the user in legacy_api_password auth provider."""
    provider = auth.get_auth_provider("legacy_api_password", None)
    return await auth.async_get_or_create_user(
        await provider.async_get_or_create_credentials({})
    )


@pytest.fixture
def app(opp):
    """Fixture to set up a web.Application."""
    app = web.Application()
    app["opp"] = opp
    app.router.add_get("/", mock_handler)
    setup_real_ip(app, False, [])
    return app


@pytest.fixture
def app2(opp):
    """Fixture to set up a web.Application without real_ip middleware."""
    app = web.Application()
    app["opp"] = opp
    app.router.add_get("/", mock_handler)
    return app


@pytest.fixture
def trusted_networks_auth(opp):
    """Load trusted networks auth provider."""
    prv = trusted_networks.TrustedNetworksAuthProvider(
        opp,
        opp.auth._store,
        {"type": "trusted_networks", "trusted_networks": TRUSTED_NETWORKS},
    )
    opp.auth._providers[(prv.type, prv.id)] = prv
    return prv


async def test_auth_middleware_loaded_by_default(opp):
    """Test accessing to server from banned IP when feature is off."""
    with patch("openpeerpower.components.http.setup_auth") as mock_setup:
        await async_setup_component(opp, "http", {"http": {}})

    assert len(mock_setup.mock_calls) == 1


async def test_cant_access_with_password_in_header(
    app, aiohttp_client, legacy_auth, opp
):
    """Test access with password in header."""
    setup_auth(opp, app)
    client = await aiohttp_client(app)

    req = await client.get("/", headers={HTTP_HEADER_HA_AUTH: API_PASSWORD})
    assert req.status == 401

    req = await client.get("/", headers={HTTP_HEADER_HA_AUTH: "wrong-pass"})
    assert req.status == 401


async def test_cant_access_with_password_in_query(
    app, aiohttp_client, legacy_auth, opp
):
    """Test access with password in URL."""
    setup_auth(opp, app)
    client = await aiohttp_client(app)

    resp = await client.get("/", params={"api_password": API_PASSWORD})
    assert resp.status == 401

    resp = await client.get("/")
    assert resp.status == 401

    resp = await client.get("/", params={"api_password": "wrong-password"})
    assert resp.status == 401


async def test_basic_auth_does_not_work(app, aiohttp_client, opp, legacy_auth):
    """Test access with basic authentication."""
    setup_auth(opp, app)
    client = await aiohttp_client(app)

    req = await client.get("/", auth=BasicAuth("openpeerpower", API_PASSWORD))
    assert req.status == 401

    req = await client.get("/", auth=BasicAuth("wrong_username", API_PASSWORD))
    assert req.status == 401

    req = await client.get("/", auth=BasicAuth("openpeerpower", "wrong password"))
    assert req.status == 401

    req = await client.get("/", headers={"authorization": "NotBasic abcdefg"})
    assert req.status == 401


async def test_cannot_access_with_trusted_ip(
    opp, app2, trusted_networks_auth, aiohttp_client, opp_owner_user
):
    """Test access with an untrusted ip address."""
    setup_auth(opp, app2)

    set_mock_ip = mock_real_ip(app2)
    client = await aiohttp_client(app2)

    for remote_addr in UNTRUSTED_ADDRESSES:
        set_mock_ip(remote_addr)
        resp = await client.get("/")
        assert resp.status == 401, "{} shouldn't be trusted".format(remote_addr)

    for remote_addr in TRUSTED_ADDRESSES:
        set_mock_ip(remote_addr)
        resp = await client.get("/")
        assert resp.status == 401, "{} shouldn't be trusted".format(remote_addr)


async def test_auth_active_access_with_access_token_in_header(
    opp, app, aiohttp_client, opp_access_token
):
    """Test access with access token in header."""
    token = opp_access_token
    setup_auth(opp, app)
    client = await aiohttp_client(app)
    refresh_token = await opp.auth.async_validate_access_token(opp_access_token)

    req = await client.get("/", headers={"Authorization": "Bearer {}".format(token)})
    assert req.status == 200
    assert await req.json() == {"user_id": refresh_token.user.id}

    req = await client.get("/", headers={"AUTHORIZATION": "Bearer {}".format(token)})
    assert req.status == 200
    assert await req.json() == {"user_id": refresh_token.user.id}

    req = await client.get("/", headers={"authorization": "Bearer {}".format(token)})
    assert req.status == 200
    assert await req.json() == {"user_id": refresh_token.user.id}

    req = await client.get("/", headers={"Authorization": token})
    assert req.status == 401

    req = await client.get("/", headers={"Authorization": "BEARER {}".format(token)})
    assert req.status == 401

    refresh_token = await opp.auth.async_validate_access_token(opp_access_token)
    refresh_token.user.is_active = False
    req = await client.get("/", headers={"Authorization": "Bearer {}".format(token)})
    assert req.status == 401


async def test_auth_active_access_with_trusted_ip(
    opp, app2, trusted_networks_auth, aiohttp_client, opp_owner_user
):
    """Test access with an untrusted ip address."""
    setup_auth(opp, app2)

    set_mock_ip = mock_real_ip(app2)
    client = await aiohttp_client(app2)

    for remote_addr in UNTRUSTED_ADDRESSES:
        set_mock_ip(remote_addr)
        resp = await client.get("/")
        assert resp.status == 401, "{} shouldn't be trusted".format(remote_addr)

    for remote_addr in TRUSTED_ADDRESSES:
        set_mock_ip(remote_addr)
        resp = await client.get("/")
        assert resp.status == 401, "{} shouldn't be trusted".format(remote_addr)


async def test_auth_legacy_support_api_password_cannot_access(
    app, aiohttp_client, legacy_auth, opp
):
    """Test access using api_password if auth.support_legacy."""
    setup_auth(opp, app)
    client = await aiohttp_client(app)

    req = await client.get("/", headers={HTTP_HEADER_HA_AUTH: API_PASSWORD})
    assert req.status == 401

    resp = await client.get("/", params={"api_password": API_PASSWORD})
    assert resp.status == 401

    req = await client.get("/", auth=BasicAuth("openpeerpower", API_PASSWORD))
    assert req.status == 401


async def test_auth_access_signed_path(opp, app, aiohttp_client, opp_access_token):
    """Test access with signed url."""
    app.router.add_post("/", mock_handler)
    app.router.add_get("/another_path", mock_handler)
    setup_auth(opp, app)
    client = await aiohttp_client(app)

    refresh_token = await opp.auth.async_validate_access_token(opp_access_token)

    signed_path = async_sign_path(opp, refresh_token.id, "/", timedelta(seconds=5))

    req = await client.get(signed_path)
    assert req.status == 200
    data = await req.json()
    assert data["user_id"] == refresh_token.user.id

    # Use signature on other path
    req = await client.get("/another_path?{}".format(signed_path.split("?")[1]))
    assert req.status == 401

    # We only allow GET
    req = await client.post(signed_path)
    assert req.status == 401

    # Never valid as expired in the past.
    expired_signed_path = async_sign_path(
        opp, refresh_token.id, "/", timedelta(seconds=-5)
    )

    req = await client.get(expired_signed_path)
    assert req.status == 401

    # refresh token gone should also invalidate signature
    await opp.auth.async_remove_refresh_token(refresh_token)
    req = await client.get(signed_path)
    assert req.status == 401
