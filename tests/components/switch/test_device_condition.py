"""The test for switch device automation."""
from datetime import timedelta
from unittest.mock import patch

import pytest

import openpeerpower.components.automation as automation
from openpeerpower.components.switch import DOMAIN
from openpeerpower.const import CONF_PLATFORM, STATE_OFF, STATE_ON
from openpeerpower.helpers import device_registry
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_get_device_automation_capabilities,
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


@pytest.fixture
def calls(opp):
    """Track calls to a mock service."""
    return async_mock_service(opp, "test", "automation")


async def test_get_conditions(opp, device_reg, entity_reg):
    """Test we get the expected conditions from a switch."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_opp(opp)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_reg.async_get_or_create(DOMAIN, "test", "5678", device_id=device_entry.id)
    expected_conditions = [
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": "is_off",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
        {
            "condition": "device",
            "domain": DOMAIN,
            "type": "is_on",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
    ]
    conditions = await async_get_device_automations(opp, "condition", device_entry.id)
    assert conditions == expected_conditions


async def test_get_condition_capabilities(opp, device_reg, entity_reg):
    """Test we get the expected capabilities from a switch condition."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_opp(opp)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_reg.async_get_or_create(DOMAIN, "test", "5678", device_id=device_entry.id)
    expected_capabilities = {
        "extra_fields": [
            {"name": "for", "optional": True, "type": "positive_time_period_dict"}
        ]
    }
    conditions = await async_get_device_automations(opp, "condition", device_entry.id)
    for condition in conditions:
        capabilities = await async_get_device_automation_capabilities(
            opp, "condition", condition
        )
        assert capabilities == expected_capabilities


async def test_if_state(opp, calls):
    """Test for turn_on and turn_off conditions."""
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
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": "",
                            "entity_id": ent1.entity_id,
                            "type": "is_on",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_on {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(("platform", "event.event_type"))
                        },
                    },
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event2"},
                    "condition": [
                        {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": "",
                            "entity_id": ent1.entity_id,
                            "type": "is_off",
                        }
                    ],
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "is_off {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(("platform", "event.event_type"))
                        },
                    },
                },
            ]
        },
    )
    await opp.async_block_till_done()
    assert opp.states.get(ent1.entity_id).state == STATE_ON
    assert len(calls) == 0

    opp.bus.async_fire("test_event1")
    opp.bus.async_fire("test_event2")
    await opp.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data["some"] == "is_on event - test_event1"

    opp.states.async_set(ent1.entity_id, STATE_OFF)
    opp.bus.async_fire("test_event1")
    opp.bus.async_fire("test_event2")
    await opp.async_block_till_done()
    assert len(calls) == 2
    assert calls[1].data["some"] == "is_off event - test_event2"


async def test_if_fires_on_for_condition(opp, calls):
    """Test for firing if condition is on with delay."""
    point1 = dt_util.utcnow()
    point2 = point1 + timedelta(seconds=10)
    point3 = point2 + timedelta(seconds=10)

    platform = getattr(opp.components, f"test.{DOMAIN}")

    platform.init()
    assert await async_setup_component(opp, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    ent1, ent2, ent3 = platform.ENTITIES

    with patch("openpeerpower.core.dt_util.utcnow") as mock_utcnow:
        mock_utcnow.return_value = point1
        assert await async_setup_component(
            opp,
            automation.DOMAIN,
            {
                automation.DOMAIN: [
                    {
                        "trigger": {"platform": "event", "event_type": "test_event1"},
                        "condition": {
                            "condition": "device",
                            "domain": DOMAIN,
                            "device_id": "",
                            "entity_id": ent1.entity_id,
                            "type": "is_off",
                            "for": {"seconds": 5},
                        },
                        "action": {
                            "service": "test.automation",
                            "data_template": {
                                "some": "is_off {{ trigger.%s }}"
                                % "}} - {{ trigger.".join(
                                    ("platform", "event.event_type")
                                )
                            },
                        },
                    }
                ]
            },
        )
        await opp.async_block_till_done()
        assert opp.states.get(ent1.entity_id).state == STATE_ON
        assert len(calls) == 0

        opp.bus.async_fire("test_event1")
        await opp.async_block_till_done()
        assert len(calls) == 0

        # Time travel 10 secs into the future
        mock_utcnow.return_value = point2
        opp.bus.async_fire("test_event1")
        await opp.async_block_till_done()
        assert len(calls) == 0

        opp.states.async_set(ent1.entity_id, STATE_OFF)
        opp.bus.async_fire("test_event1")
        await opp.async_block_till_done()
        assert len(calls) == 0

        # Time travel 20 secs into the future
        mock_utcnow.return_value = point3
        opp.bus.async_fire("test_event1")
        await opp.async_block_till_done()
        assert len(calls) == 1
        assert calls[0].data["some"] == "is_off event - test_event1"
