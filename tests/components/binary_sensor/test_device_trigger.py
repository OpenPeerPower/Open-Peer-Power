"""The test for binary_sensor device automation."""
from datetime import timedelta

import pytest

import openpeerpower.components.automation as automation
from openpeerpower.components.binary_sensor import DEVICE_CLASSES, DOMAIN
from openpeerpower.components.binary_sensor.device_trigger import ENTITY_TRIGGERS
from openpeerpower.const import CONF_PLATFORM, STATE_OFF, STATE_ON
from openpeerpower.helpers import device_registry
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
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


async def test_get_triggers(opp, device_reg, entity_reg):
    """Test we get the expected triggers from a binary_sensor."""
    platform = getattr(opp.components, f"test.{DOMAIN}")
    platform.init()

    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_opp(opp)
    device_entry = device_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(device_registry.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    for device_class in DEVICE_CLASSES:
        entity_reg.async_get_or_create(
            DOMAIN,
            "test",
            platform.ENTITIES[device_class].unique_id,
            device_id=device_entry.id,
        )

    assert await async_setup_component(opp, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger["type"],
            "device_id": device_entry.id,
            "entity_id": platform.ENTITIES[device_class].entity_id,
        }
        for device_class in DEVICE_CLASSES
        for trigger in ENTITY_TRIGGERS[device_class]
    ]
    triggers = await async_get_device_automations(opp, "trigger", device_entry.id)
    assert triggers == expected_triggers


async def test_get_trigger_capabilities(opp, device_reg, entity_reg):
    """Test we get the expected capabilities from a binary_sensor trigger."""
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
    triggers = await async_get_device_automations(opp, "trigger", device_entry.id)
    for trigger in triggers:
        capabilities = await async_get_device_automation_capabilities(
            opp, "trigger", trigger
        )
        assert capabilities == expected_capabilities


async def test_if_fires_on_state_change(opp, calls):
    """Test for on and off triggers firing."""
    platform = getattr(opp.components, f"test.{DOMAIN}")
    platform.init()
    assert await async_setup_component(opp, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    sensor1 = platform.ENTITIES["battery"]

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": sensor1.entity_id,
                        "type": "bat_low",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "bat_low {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                (
                                    "platform",
                                    "entity_id",
                                    "from_state.state",
                                    "to_state.state",
                                    "for",
                                )
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": sensor1.entity_id,
                        "type": "not_bat_low",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "not_bat_low {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                (
                                    "platform",
                                    "entity_id",
                                    "from_state.state",
                                    "to_state.state",
                                    "for",
                                )
                            )
                        },
                    },
                },
            ]
        },
    )
    await opp.async_block_till_done()
    assert opp.states.get(sensor1.entity_id).state == STATE_ON
    assert len(calls) == 0

    opp.states.async_set(sensor1.entity_id, STATE_OFF)
    await opp.async_block_till_done()
    assert len(calls) == 1
    assert calls[0].data["some"] == "not_bat_low device - {} - on - off - None".format(
        sensor1.entity_id
    )

    opp.states.async_set(sensor1.entity_id, STATE_ON)
    await opp.async_block_till_done()
    assert len(calls) == 2
    assert calls[1].data["some"] == "bat_low device - {} - off - on - None".format(
        sensor1.entity_id
    )


async def test_if_fires_on_state_change_with_for(opp, calls):
    """Test for triggers firing with delay."""
    platform = getattr(opp.components, f"test.{DOMAIN}")

    platform.init()
    assert await async_setup_component(opp, DOMAIN, {DOMAIN: {CONF_PLATFORM: "test"}})

    sensor1 = platform.ENTITIES["battery"]

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": sensor1.entity_id,
                        "type": "turned_off",
                        "for": {"seconds": 5},
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": "turn_off {{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                (
                                    "platform",
                                    "entity_id",
                                    "from_state.state",
                                    "to_state.state",
                                    "for",
                                )
                            )
                        },
                    },
                }
            ]
        },
    )
    await opp.async_block_till_done()
    assert opp.states.get(sensor1.entity_id).state == STATE_ON
    assert len(calls) == 0

    opp.states.async_set(sensor1.entity_id, STATE_OFF)
    await opp.async_block_till_done()
    assert len(calls) == 0
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert len(calls) == 1
    await opp.async_block_till_done()
    assert calls[0].data["some"] == "turn_off device - {} - on - off - 0:00:05".format(
        sensor1.entity_id
    )
