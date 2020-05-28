"""Test the cloud component."""
from unittest.mock import patch

import pytest

from openpeerpower.components import cloud
from openpeerpower.components.cloud.const import DOMAIN
from openpeerpower.components.cloud.prefs import STORAGE_KEY
from openpeerpower.const import EVENT_OPENPEERPOWER_START, EVENT_OPENPEERPOWER_STOP
from openpeerpower.core import Context
from openpeerpower.exceptions import Unauthorized
from openpeerpower.setup import async_setup_component

from tests.common import mock_coro


async def test_constructor_loads_info_from_config(opp):
    """Test non-dev mode loads info from SERVERS constant."""
    with patch("opp_nabucasa.Cloud.start", return_value=mock_coro()):
        result = await async_setup_component(
            opp,
            "cloud",
            {
                "http": {},
                "cloud": {
                    cloud.CONF_MODE: cloud.MODE_DEV,
                    "cognito_client_id": "test-cognito_client_id",
                    "user_pool_id": "test-user_pool_id",
                    "region": "test-region",
                    "relayer": "test-relayer",
                    "subscription_info_url": "http://test-subscription-info-url",
                    "cloudhook_create_url": "http://test-cloudhook_create_url",
                    "remote_api_url": "http://test-remote_api_url",
                    "alexa_access_token_url": "http://test-alexa-token-url",
                    "acme_directory_server": "http://test-acme-directory-server",
                    "google_actions_report_state_url": "http://test-google-actions-report-state-url",
                },
            },
        )
        assert result

    cl = opp.data["cloud"]
    assert cl.mode == cloud.MODE_DEV
    assert cl.cognito_client_id == "test-cognito_client_id"
    assert cl.user_pool_id == "test-user_pool_id"
    assert cl.region == "test-region"
    assert cl.relayer == "test-relayer"
    assert cl.subscription_info_url == "http://test-subscription-info-url"
    assert cl.cloudhook_create_url == "http://test-cloudhook_create_url"
    assert cl.remote_api_url == "http://test-remote_api_url"
    assert cl.alexa_access_token_url == "http://test-alexa-token-url"
    assert cl.acme_directory_server == "http://test-acme-directory-server"
    assert (
        cl.google_actions_report_state_url
        == "http://test-google-actions-report-state-url"
    )


async def test_remote_services(opp, mock_cloud_fixture, opp_read_only_user):
    """Setup cloud component and test services."""
    cloud = opp.data[DOMAIN]

    assert opp.services.has_service(DOMAIN, "remote_connect")
    assert opp.services.has_service(DOMAIN, "remote_disconnect")

    with patch(
        "opp_nabucasa.remote.RemoteUI.connect", return_value=mock_coro()
    ) as mock_connect:
        await opp.services.async_call(DOMAIN, "remote_connect", blocking=True)

    assert mock_connect.called
    assert cloud.client.remote_autostart

    with patch(
        "opp_nabucasa.remote.RemoteUI.disconnect", return_value=mock_coro()
    ) as mock_disconnect:
        await opp.services.async_call(DOMAIN, "remote_disconnect", blocking=True)

    assert mock_disconnect.called
    assert not cloud.client.remote_autostart

    # Test admin access required
    non_admin_context = Context(user_id=opp_read_only_user.id)

    with patch(
        "opp_nabucasa.remote.RemoteUI.connect", return_value=mock_coro()
    ) as mock_connect, pytest.raises(Unauthorized):
        await opp.services.async_call(
            DOMAIN, "remote_connect", blocking=True, context=non_admin_context
        )

    assert mock_connect.called is False

    with patch(
        "opp_nabucasa.remote.RemoteUI.disconnect", return_value=mock_coro()
    ) as mock_disconnect, pytest.raises(Unauthorized):
        await opp.services.async_call(
            DOMAIN, "remote_disconnect", blocking=True, context=non_admin_context
        )

    assert mock_disconnect.called is False


async def test_startup_shutdown_events(opp, mock_cloud_fixture):
    """Test if the cloud will start on startup event."""
    with patch("opp_nabucasa.Cloud.start", return_value=mock_coro()) as mock_start:
        opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
        await opp.async_block_till_done()

    assert mock_start.called

    with patch("opp_nabucasa.Cloud.stop", return_value=mock_coro()) as mock_stop:
        opp.bus.async_fire(EVENT_OPENPEERPOWER_STOP)
        await opp.async_block_till_done()

    assert mock_stop.called


async def test_setup_existing_cloud_user(opp, opp_storage):
    """Test setup with API push default data."""
    user = await opp.auth.async_create_system_user("Cloud test")
    opp_storage[STORAGE_KEY] = {"version": 1, "data": {"cloud_user": user.id}}
    with patch("opp_nabucasa.Cloud.start", return_value=mock_coro()):
        result = await async_setup_component(
            opp,
            "cloud",
            {
                "http": {},
                "cloud": {
                    cloud.CONF_MODE: cloud.MODE_DEV,
                    "cognito_client_id": "test-cognito_client_id",
                    "user_pool_id": "test-user_pool_id",
                    "region": "test-region",
                    "relayer": "test-relayer",
                },
            },
        )
        assert result

    assert opp_storage[STORAGE_KEY]["data"]["cloud_user"] == user.id


async def test_on_connect(opp, mock_cloud_fixture):
    """Test cloud on connect triggers."""
    cl = opp.data["cloud"]

    assert len(cl.iot._on_connect) == 3

    assert len(opp.states.async_entity_ids("binary_sensor")) == 0

    assert "async_setup" in str(cl.iot._on_connect[-1])
    await cl.iot._on_connect[-1]()
    await opp.async_block_till_done()

    assert len(opp.states.async_entity_ids("binary_sensor")) == 1

    with patch(
        "openpeerpower.helpers.discovery.async_load_platform", side_effect=mock_coro
    ) as mock_load:
        await cl.iot._on_connect[-1]()
        await opp.async_block_till_done()

    assert len(mock_load.mock_calls) == 0


async def test_remote_ui_url(opp, mock_cloud_fixture):
    """Test getting remote ui url."""
    cl = opp.data["cloud"]

    # Not logged in
    with pytest.raises(cloud.CloudNotAvailable):
        cloud.async_remote_ui_url(opp)

    with patch.object(cloud, "async_is_logged_in", return_value=True):
        # Remote not enabled
        with pytest.raises(cloud.CloudNotAvailable):
            cloud.async_remote_ui_url(opp)

        await cl.client.prefs.async_update(remote_enabled=True)

        # No instance domain
        with pytest.raises(cloud.CloudNotAvailable):
            cloud.async_remote_ui_url(opp)

        cl.remote._instance_domain = "example.com"

        assert cloud.async_remote_ui_url(opp) == "https://example.com"
