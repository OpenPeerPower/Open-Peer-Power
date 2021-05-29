"""The tests for the Open Peer Power HTTP component."""
from ipaddress import ip_network
import logging
import unittest
from unittest.mock import patch

import openpeerpower.components.http as http
from openpeerpower.setup import async_setup_component
from openpeerpower.util.ssl import server_context_intermediate, server_context_modern


class TestView(http.OpenPeerPowerView):
    """Test the HTTP views."""

    name = "test"
    url = "/hello"

    async def get(self, request):
        """Return a get request."""
        return "hello"


async def test_registering_view_while_running(opp, aiohttp_client, aiohttp_unused_port):
    """Test that we can register a view while the server is running."""
    await async_setup_component(
        opp, http.DOMAIN, {http.DOMAIN: {http.CONF_SERVER_PORT: aiohttp_unused_port()}}
    )

    await opp.async_start()
    # This raises a RuntimeError if app is frozen
    opp.http.register_view(TestView)


class TestApiConfig(unittest.TestCase):
    """Test API configuration methods."""

    def test_api_base_url_with_domain(opp):
        """Test setting API URL with domain."""
        api_config = http.ApiConfig("example.com")
        assert api_config.base_url == "http://example.com:8123"

    def test_api_base_url_with_ip(opp):
        """Test setting API URL with IP."""
        api_config = http.ApiConfig("1.1.1.1")
        assert api_config.base_url == "http://1.1.1.1:8123"

    def test_api_base_url_with_ip_and_port(opp):
        """Test setting API URL with IP and port."""
        api_config = http.ApiConfig("1.1.1.1", 8124)
        assert api_config.base_url == "http://1.1.1.1:8124"

    def test_api_base_url_with_protocol(opp):
        """Test setting API URL with protocol."""
        api_config = http.ApiConfig("https://example.com")
        assert api_config.base_url == "https://example.com:8123"

    def test_api_base_url_with_protocol_and_port(opp):
        """Test setting API URL with protocol and port."""
        api_config = http.ApiConfig("https://example.com", 433)
        assert api_config.base_url == "https://example.com:433"

    def test_api_base_url_with_ssl_enable(opp):
        """Test setting API URL with use_ssl enabled."""
        api_config = http.ApiConfig("example.com", use_ssl=True)
        assert api_config.base_url == "https://example.com:8123"

    def test_api_base_url_with_ssl_enable_and_port(opp):
        """Test setting API URL with use_ssl enabled and port."""
        api_config = http.ApiConfig("1.1.1.1", use_ssl=True, port=8888)
        assert api_config.base_url == "https://1.1.1.1:8888"

    def test_api_base_url_with_protocol_and_ssl_enable(opp):
        """Test setting API URL with specific protocol and use_ssl enabled."""
        api_config = http.ApiConfig("http://example.com", use_ssl=True)
        assert api_config.base_url == "http://example.com:8123"

    def test_api_base_url_removes_trailing_slash(opp):
        """Test a trialing slash is removed when setting the API URL."""
        api_config = http.ApiConfig("http://example.com/")
        assert api_config.base_url == "http://example.com:8123"


async def test_api_base_url_with_domain(opp):
    """Test setting API URL."""
    result = await async_setup_component(
        opp, "http", {"http": {"base_url": "example.com"}}
    )
    assert result
    assert opp.config.api.base_url == "http://example.com"


async def test_api_base_url_with_ip(opp):
    """Test setting api url."""
    result = await async_setup_component(
        opp, "http", {"http": {"server_host": "1.1.1.1"}}
    )
    assert result
    assert opp.config.api.base_url == "http://1.1.1.1:8123"


async def test_api_base_url_with_ip_port(opp):
    """Test setting api url."""
    result = await async_setup_component(
        opp, "http", {"http": {"base_url": "1.1.1.1:8124"}}
    )
    assert result
    assert opp.config.api.base_url == "http://1.1.1.1:8124"


async def test_api_no_base_url(opp):
    """Test setting api url."""
    result = await async_setup_component(opp, "http", {"http": {}})
    assert result
    assert opp.config.api.base_url == "http://127.0.0.1:8123"


async def test_api_base_url_removes_trailing_slash(opp):
    """Test setting api url."""
    result = await async_setup_component(
        opp, "http", {"http": {"base_url": "https://example.com/"}}
    )
    assert result
    assert opp.config.api.base_url == "https://example.com"


async def test_not_log_password(opp, aiohttp_client, caplog, legacy_auth):
    """Test access with password doesn't get logged."""
    assert await async_setup_component(opp, "api", {"http": {}})
    client = await aiohttp_client(opp.http.app)
    logging.getLogger("aiohttp.access").setLevel(logging.INFO)

    resp = await client.get("/api/", params={"api_password": "test-password"})

    assert resp.status == 401
    logs = caplog.text

    # Ensure we don't log API passwords
    assert "/api/" in logs
    assert "some-pass" not in logs


async def test_proxy_config(opp):
    """Test use_x_forwarded_for must config together with trusted_proxies."""
    assert (
        await async_setup_component(
            opp,
            "http",
            {
                "http": {
                    http.CONF_USE_X_FORWARDED_FOR: True,
                    http.CONF_TRUSTED_PROXIES: ["127.0.0.1"],
                }
            },
        )
        is True
    )


async def test_proxy_config_only_use_xff(opp):
    """Test use_x_forwarded_for must config together with trusted_proxies."""
    assert (
        await async_setup_component(
            opp, "http", {"http": {http.CONF_USE_X_FORWARDED_FOR: True}}
        )
        is not True
    )


async def test_proxy_config_only_trust_proxies(opp):
    """Test use_x_forwarded_for must config together with trusted_proxies."""
    assert (
        await async_setup_component(
            opp, "http", {"http": {http.CONF_TRUSTED_PROXIES: ["127.0.0.1"]}}
        )
        is not True
    )


async def test_ssl_profile_defaults_modern(opp):
    """Test default ssl profile."""
    assert await async_setup_component(opp, "http", {}) is True

    opp.http.ssl_certificate = "bla"

    with patch("ssl.SSLContext.load_cert_chain"), patch(
        "openpeerpower.util.ssl.server_context_modern",
        side_effect=server_context_modern,
    ) as mock_context:
        await opp.async_start()
        await opp.async_block_till_done()

    assert len(mock_context.mock_calls) == 1


async def test_ssl_profile_change_intermediate(opp):
    """Test setting ssl profile to intermediate."""
    assert (
        await async_setup_component(
            opp, "http", {"http": {"ssl_profile": "intermediate"}}
        )
        is True
    )

    opp.http.ssl_certificate = "bla"

    with patch("ssl.SSLContext.load_cert_chain"), patch(
        "openpeerpower.util.ssl.server_context_intermediate",
        side_effect=server_context_intermediate,
    ) as mock_context:
        await opp.async_start()
        await opp.async_block_till_done()

    assert len(mock_context.mock_calls) == 1


async def test_ssl_profile_change_modern(opp):
    """Test setting ssl profile to modern."""
    assert (
        await async_setup_component(opp, "http", {"http": {"ssl_profile": "modern"}})
        is True
    )

    opp.http.ssl_certificate = "bla"

    with patch("ssl.SSLContext.load_cert_chain"), patch(
        "openpeerpower.util.ssl.server_context_modern",
        side_effect=server_context_modern,
    ) as mock_context:
        await opp.async_start()
        await opp.async_block_till_done()

    assert len(mock_context.mock_calls) == 1


async def test_cors_defaults(opp):
    """Test the CORS default settings."""
    with patch("openpeerpower.components.http.setup_cors") as mock_setup:
        assert await async_setup_component(opp, "http", {})

    assert len(mock_setup.mock_calls) == 1
    assert mock_setup.mock_calls[0][1][1] == ["https://cast.open-peer-power.io"]


async def test_storing_config(opp, aiohttp_client, aiohttp_unused_port):
    """Test that we store last working config."""
    config = {
        http.CONF_SERVER_PORT: aiohttp_unused_port(),
        "use_x_forwarded_for": True,
        "trusted_proxies": ["192.168.1.100"],
    }

    assert await async_setup_component(opp, http.DOMAIN, {http.DOMAIN: config})

    await opp.async_start()
    restored = await opp.components.http.async_get_last_config()
    restored["trusted_proxies"][0] = ip_network(restored["trusted_proxies"][0])

    assert restored == http.HTTP_SCHEMA(config)
