"""Test account link services."""
import asyncio
import logging
from time import time
from unittest.mock import Mock, patch

import pytest

from openpeerpower import config_entries, data_entry_flow
from openpeerpower.components.cloud import account_link
from openpeerpower.helpers import config_entry_oauth2_flow
from openpeerpower.util.dt import utcnow

from tests.common import async_fire_time_changed, mock_coro, mock_platform

TEST_DOMAIN = "oauth2_test"


@pytest.fixture
def flow_handler(opp):
    """Return a registered config flow."""

    mock_platform(opp, f"{TEST_DOMAIN}.config_flow")

    class TestFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler):
        """Test flow handler."""

        DOMAIN = TEST_DOMAIN

        @property
        def logger(self) -> logging.Logger:
            """Return logger."""
            return logging.getLogger(__name__)

    with patch.dict(config_entries.HANDLERS, {TEST_DOMAIN: TestFlowHandler}):
        yield TestFlowHandler


async def test_setup_provide_implementation(opp):
    """Test that we provide implementations."""
    account_link.async_setup(opp)

    with patch(
        "openpeerpower.components.cloud.account_link._get_services",
        side_effect=lambda _: mock_coro(
            [
                {"service": "test", "min_version": "0.1.0"},
                {"service": "too_new", "min_version": "100.0.0"},
            ]
        ),
    ):
        assert (
            await config_entry_oauth2_flow.async_get_implementations(
                opp, "non_existing"
            )
            == {}
        )
        assert (
            await config_entry_oauth2_flow.async_get_implementations(opp, "too_new")
            == {}
        )
        implementations = await config_entry_oauth2_flow.async_get_implementations(
            opp, "test"
        )

    assert "cloud" in implementations
    assert implementations["cloud"].domain == "cloud"
    assert implementations["cloud"].service == "test"
    assert implementations["cloud"].opp is opp


async def test_get_services_cached(opp):
    """Test that we cache services."""
    opp.data["cloud"] = None

    services = 1

    with patch.object(account_link, "CACHE_TIMEOUT", 0), patch(
        "opp_cloud.account_link.async_fetch_available_services",
        side_effect=lambda _: mock_coro(services),
    ) as mock_fetch:
        assert await account_link._get_services(opp) == 1

        services = 2

        assert len(mock_fetch.mock_calls) == 1
        assert await account_link._get_services(opp) == 1

        services = 3
        opp.data.pop(account_link.DATA_SERVICES)
        assert await account_link._get_services(opp) == 3

        services = 4
        async_fire_time_changed(opp, utcnow())
        await opp.async_block_till_done()

        # Check cache purged
        assert await account_link._get_services(opp) == 4


async def test_implementation(opp, flow_handler):
    """Test Cloud OAuth2 implementation."""
    opp.data["cloud"] = None

    impl = account_link.CloudOAuth2Implementation(opp, "test")
    assert impl.name == "Open Peer Power Cloud"
    assert impl.domain == "cloud"

    flow_handler.async_register_implementation(opp, impl)

    flow_finished = asyncio.Future()

    helper = Mock(
        async_get_authorize_url=Mock(return_value=mock_coro("http://example.com/auth")),
        async_get_tokens=Mock(return_value=flow_finished),
    )

    with patch(
        "opp_cloud.account_link.AuthorizeAccountHelper", return_value=helper
    ):
        result = await opp.config_entries.flow.async_init(
            TEST_DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_EXTERNAL_STEP
    assert result["url"] == "http://example.com/auth"

    flow_finished.set_result(
        {
            "refresh_token": "mock-refresh",
            "access_token": "mock-access",
            "expires_in": 10,
            "token_type": "bearer",
        }
    )
    await opp.async_block_till_done()

    # Flow finished!
    result = await opp.config_entries.flow.async_configure(result["flow_id"])

    assert result["data"]["auth_implementation"] == "cloud"

    expires_at = result["data"]["token"].pop("expires_at")
    assert round(expires_at - time()) == 10

    assert result["data"]["token"] == {
        "refresh_token": "mock-refresh",
        "access_token": "mock-access",
        "token_type": "bearer",
        "expires_in": 10,
    }

    entry = opp.config_entries.async_entries(TEST_DOMAIN)[0]

    assert (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            opp, entry
        )
        is impl
    )
