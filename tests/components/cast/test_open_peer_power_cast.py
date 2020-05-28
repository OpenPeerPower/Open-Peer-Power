"""Test Open Peer Power Cast."""
from unittest.mock import Mock, patch

from openpeerpower.components.cast import open_peer_power_cast

from tests.common import MockConfigEntry, async_mock_signal


async def test_service_show_view(opp):
    """Test we don't set app id in prod."""
    opp.config.api = Mock(base_url="http://example.com")
    await open_peer_power_cast.async_setup_op_cast(opp, MockConfigEntry())
    calls = async_mock_signal(opp, open_peer_power_cast.SIGNAL_OPP_CAST_SHOW_VIEW)

    await opp.services.async_call(
        "cast",
        "show_devcon_view",
        {"entity_id": "media_player.kitchen", "view_path": "mock_path"},
        blocking=True,
    )

    assert len(calls) == 1
    controller, entity_id, view_path = calls[0]
    assert controller.opp_url == "http://example.com"
    assert controller.client_id is None
    # Verify user did not accidentally submit their dev app id
    assert controller.supporting_app_id == "B12CE3CA"
    assert entity_id == "media_player.kitchen"
    assert view_path == "mock_path"


async def test_use_cloud_url(opp):
    """Test that we fall back to cloud url."""
    opp.config.api = Mock(base_url="http://example.com")
    await open_peer_power_cast.async_setup_op_cast(opp, MockConfigEntry())
    calls = async_mock_signal(opp, open_peer_power_cast.SIGNAL_OPP_CAST_SHOW_VIEW)

    with patch(
        "openpeerpower.components.cloud.async_remote_ui_url",
        return_value="https://something.nabu.acas",
    ):
        await opp.services.async_call(
            "cast",
            "show_devcon_view",
            {"entity_id": "media_player.kitchen", "view_path": "mock_path"},
            blocking=True,
        )

    assert len(calls) == 1
    controller = calls[0][0]
    assert controller.opp_url == "https://something.nabu.acas"
