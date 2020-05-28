"""The test for switch device automation."""
import pytest

import openpeerpower.components.automation as automation
from openpeerpower.components.device_automation import (
    _async_get_device_automations as async_get_device_automations,
)
from openpeerpower.components.switch import DOMAIN
from openpeerpower.const import CONF_PLATFORM, STATE_OFF, STATE_ON
from openpeerpower.helpers import device_registry
from openpeerpower.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
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


@pytest.fixture
def calls(opp):
    """Track calls to a mock service."""
    return async_mock_service(opp, "test", "automation")


async def test_get_actions(opp, device_reg, entity_reg):
    """Test we get the expected actions from a switch."""
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
            "type": "turn_off",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
        {
            "domain": DOMAIN,
            "type": "turn_on",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
        {
            "domain": DOMAIN,
            "type": "toggle",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
    ]
    actions = await async_get_device_automations(opp, "action", device_entry.id)
    assert actions == expected_actions


async def test_action(opp, calls):
    """Test for turn_on and turn_off actions."""
    platform = getattr(opp.components, f"test.{DOMAIN}")

    platform.init()
    assert await async_setup_component(opp, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    ent1, ent2, ent3 = platform.ENTITIES

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event1"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": ent1.entity_id,
                        "type": "turn_off",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event2"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": ent1.entity_id,
                        "type": "turn_on",
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event3"},
                    "action": {
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": ent1.entity_id,
                        "type": "toggle",
                    },
                },
            ]
        },
    )
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_ON
    assert len(calls) == 0

    opp.bus.async_fire("test_event1")
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_OFF

    opp.bus.async_fire("test_event1")
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_OFF

    opp.bus.async_fire("test_event2")
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_ON

    opp.bus.async_fire("test_event2")
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_ON

    opp.bus.async_fire("test_event3")
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_OFF

    opp.bus.async_fire("test_event3")
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_ON
