"""The tests for Vacuum device actions."""
import pytest

import openpeerpower.components.automation as automation
from openpeerpower.components.vacuum import DOMAIN
from openpeerpower.helpers import device_registry
from openpeerpower.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    assert_lists_same,
    async_get_device_automations,
    async_mock_service,
    mock_device_registry,
    mock_registry,
)


@pytest.fixture
def device_reg(opp):
    """Return an empty, loaded, registry."""
    return mock_device_registry(opp)


@pytest.fixture
def entity_reg(opp):
    """Return an empty, loaded, registry."""
    return mock_registry(opp)


async def test_get_actions(opp, device_reg, entity_reg):
    """Test we get the expected actions from a vacuum."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_opp(opp)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_reg.async_get_or_create(DOMAIN, "test", "5678", device_id=device_entry.id)
    expected_actions = [
        {
            "domain": DOMAIN,
            "type": "clean",
            "device_id": device_entry.id,
            "entity_id": "vacuum.test_5678",
        },
        {
            "domain": DOMAIN,
            "type": "dock",
            "device_id": device_entry.id,
            "entity_id": "vacuum.test_5678",
        },
    ]
    actions = await async_get_device_automations(opp, "action", device_entry.id)
    assert_lists_same(actions, expected_actions)


async def test_action(opp):
    """Test for turn_on and turn_off actions."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event_dock"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": "abcdefgh",
                        "entity_id": "vacuum.entity",
                        "type": "dock",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_clean"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": "abcdefgh",
                        "entity_id": "vacuum.entity",
                        "type": "clean",
                    },
                },
            ]
        },
    )

    dock_calls = async_mock_service(opp, "vacuum", "return_to_base")
    clean_calls = async_mock_service(opp, "vacuum", "start")

    opp.bus.async_fire("test_event_dock")
    await opp.async_block_till_done()
    assert len(dock_calls) == 1
    assert len(clean_calls) == 0

    opp.bus.async_fire("test_event_clean")
    await opp.async_block_till_done()
    assert len(dock_calls) == 1
    assert len(clean_calls) == 1
