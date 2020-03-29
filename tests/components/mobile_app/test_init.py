"""Tests for the mobile app integration."""
from openpeerpower.components.mobile_app.const import DATA_DELETED_IDS, DOMAIN

from .const import CALL_SERVICE

from tests.common import async_mock_service


async def test_unload_unloads(opp, create_registrations, webhook_client):
    """Test we clean up when we unload."""
    # Second config entry is the one without encryption
    config_entry = opp.config_entries.async_entries("mobile_app")[1]
    webhook_id = config_entry.data["webhook_id"]
    calls = async_mock_service(opp, "test", "mobile_app")

    # Test it works
    await webhook_client.post(f"/api/webhook/{webhook_id}", json=CALL_SERVICE)
    assert len(calls) == 1

    await opp.config_entries.async_unload(config_entry.entry_id)

    # Test it no longer works
    await webhook_client.post(f"/api/webhook/{webhook_id}", json=CALL_SERVICE)
    assert len(calls) == 1


async def test_remove_entry(opp, create_registrations):
    """Test we clean up when we remove entry."""
    for config_entry in opp.config_entries.async_entries("mobile_app"):
        await opp.config_entries.async_remove(config_entry.entry_id)
        assert config_entry.data["webhook_id"] in opp.data[DOMAIN][DATA_DELETED_IDS]

    dev_reg = await opp.helpers.device_registry.async_get_registry()
    assert len(dev_reg.devices) == 0

    ent_reg = await opp.helpers.entity_registry.async_get_registry()
    assert len(ent_reg.entities) == 0
