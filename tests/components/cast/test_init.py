"""Tests for the Cast config flow."""
from unittest.mock import patch

from openpeerpower import config_entries, data_entry_flow
from openpeerpower.components import cast
from openpeerpower.setup import async_setup_component

from tests.common import MockDependency, mock_coro


async def test_creating_entry_sets_up_media_player(opp):
    """Test setting up Cast loads the media player."""
    with patch(
        "openpeerpower.components.cast.media_player.async_setup_entry",
        return_value=mock_coro(True),
    ) as mock_setup, MockDependency("pychromecast", "discovery"), patch(
        "pychromecast.discovery.discover_chromecasts", return_value=True
    ):
        result = await opp.config_entries.flow.async_init(
            cast.DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM

        result = await opp.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        await opp.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_configuring_cast_creates_entry(opp):
    """Test that specifying config will create an entry."""
    with patch(
        "openpeerpower.components.cast.async_setup_entry", return_value=mock_coro(True)
    ) as mock_setup, MockDependency("pychromecast", "discovery"), patch(
        "pychromecast.discovery.discover_chromecasts", return_value=True
    ):
        await async_setup_component(
            opp, cast.DOMAIN, {"cast": {"some_config": "to_trigger_import"}}
        )
        await opp.async_block_till_done()

    assert len(mock_setup.mock_calls) == 1


async def test_not_configuring_cast_not_creates_entry(opp):
    """Test that no config will not create an entry."""
    with patch(
        "openpeerpower.components.cast.async_setup_entry", return_value=mock_coro(True)
    ) as mock_setup, MockDependency("pychromecast", "discovery"), patch(
        "pychromecast.discovery.discover_chromecasts", return_value=True
    ):
        await async_setup_component(opp, cast.DOMAIN, {})
        await opp.async_block_till_done()

    assert len(mock_setup.mock_calls) == 0
