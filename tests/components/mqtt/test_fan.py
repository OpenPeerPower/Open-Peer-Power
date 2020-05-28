"""Test MQTT fans."""
import json
from unittest.mock import ANY

from openpeerpower.components import fan, mqtt
from openpeerpower.components.mqtt.discovery import async_start
from openpeerpower.const import (
    ATTR_ASSUMED_STATE,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from openpeerpower.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_mqtt_component,
    mock_registry,
)
from tests.components.fan import common


async def test_fail_setup_if_no_command_topic(opp, mqtt_mock):
    """Test if command fails with command topic."""
    assert await async_setup_component(
        opp, fan.DOMAIN, {fan.DOMAIN: {"platform": "mqtt", "name": "test"}}
    )
    assert opp.states.get("fan.test") is None


async def test_controlling_state_via_topic(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_off": "StAtE_OfF",
                "payload_on": "StAtE_On",
                "oscillation_state_topic": "oscillation-state-topic",
                "oscillation_command_topic": "oscillation-command-topic",
                "payload_oscillation_off": "OsC_OfF",
                "payload_oscillation_on": "OsC_On",
                "speed_state_topic": "speed-state-topic",
                "speed_command_topic": "speed-command-topic",
                "payload_off_speed": "speed_OfF",
                "payload_low_speed": "speed_lOw",
                "payload_medium_speed": "speed_mEdium",
                "payload_high_speed": "speed_High",
            }
        },
    )

    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "state-topic", "StAtE_On")
    state = opp.states.get("fan.test")
    assert state.state is STATE_ON

    async_fire_mqtt_message(opp, "state-topic", "StAtE_OfF")
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get("oscillating") is False

    async_fire_mqtt_message(opp, "oscillation-state-topic", "OsC_On")
    state = opp.states.get("fan.test")
    assert state.attributes.get("oscillating") is True

    async_fire_mqtt_message(opp, "oscillation-state-topic", "OsC_OfF")
    state = opp.states.get("fan.test")
    assert state.attributes.get("oscillating") is False

    assert state.attributes.get("speed") == fan.SPEED_OFF

    async_fire_mqtt_message(opp, "speed-state-topic", "speed_lOw")
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_LOW

    async_fire_mqtt_message(opp, "speed-state-topic", "speed_mEdium")
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_MEDIUM

    async_fire_mqtt_message(opp, "speed-state-topic", "speed_High")
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_HIGH

    async_fire_mqtt_message(opp, "speed-state-topic", "speed_OfF")
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_OFF


async def test_controlling_state_via_topic_and_json_message(opp, mqtt_mock):
    """Test the controlling state via topic and JSON message."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "oscillation_state_topic": "oscillation-state-topic",
                "oscillation_command_topic": "oscillation-command-topic",
                "speed_state_topic": "speed-state-topic",
                "speed_command_topic": "speed-command-topic",
                "state_value_template": "{{ value_json.val }}",
                "oscillation_value_template": "{{ value_json.val }}",
                "speed_value_template": "{{ value_json.val }}",
            }
        },
    )

    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "state-topic", '{"val":"ON"}')
    state = opp.states.get("fan.test")
    assert state.state is STATE_ON

    async_fire_mqtt_message(opp, "state-topic", '{"val":"OFF"}')
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get("oscillating") is False

    async_fire_mqtt_message(opp, "oscillation-state-topic", '{"val":"oscillate_on"}')
    state = opp.states.get("fan.test")
    assert state.attributes.get("oscillating") is True

    async_fire_mqtt_message(opp, "oscillation-state-topic", '{"val":"oscillate_off"}')
    state = opp.states.get("fan.test")
    assert state.attributes.get("oscillating") is False

    assert state.attributes.get("speed") == fan.SPEED_OFF

    async_fire_mqtt_message(opp, "speed-state-topic", '{"val":"low"}')
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_LOW

    async_fire_mqtt_message(opp, "speed-state-topic", '{"val":"medium"}')
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_MEDIUM

    async_fire_mqtt_message(opp, "speed-state-topic", '{"val":"high"}')
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_HIGH

    async_fire_mqtt_message(opp, "speed-state-topic", '{"val":"off"}')
    state = opp.states.get("fan.test")
    assert state.attributes.get("speed") == fan.SPEED_OFF


async def test_sending_mqtt_commands_and_optimistic(opp, mqtt_mock):
    """Test optimistic mode without state topic."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "command-topic",
                "payload_off": "StAtE_OfF",
                "payload_on": "StAtE_On",
                "oscillation_command_topic": "oscillation-command-topic",
                "oscillation_state_topic": "oscillation-state-topic",
                "payload_oscillation_off": "OsC_OfF",
                "payload_oscillation_on": "OsC_On",
                "speed_command_topic": "speed-command-topic",
                "speed_state_topic": "speed-state-topic",
                "payload_off_speed": "speed_OfF",
                "payload_low_speed": "speed_lOw",
                "payload_medium_speed": "speed_mEdium",
                "payload_high_speed": "speed_High",
            }
        },
    )

    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_turn_on(opp, "fan.test")
    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "StAtE_On", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_turn_off(opp, "fan.test")
    mqtt_mock.async_publish.assert_called_once_with(
        "command-topic", "StAtE_OfF", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_oscillate(opp, "fan.test", True)
    mqtt_mock.async_publish.assert_called_once_with(
        "oscillation-command-topic", "OsC_On", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_oscillate(opp, "fan.test", False)
    mqtt_mock.async_publish.assert_called_once_with(
        "oscillation-command-topic", "OsC_OfF", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_LOW)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "speed_lOw", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_MEDIUM)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "speed_mEdium", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_HIGH)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "speed_High", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_OFF)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "speed_OfF", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)


async def test_sending_mqtt_commands_and_explicit_optimistic(opp, mqtt_mock):
    """Test optimistic mode with state topic."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "oscillation_state_topic": "oscillation-state-topic",
                "oscillation_command_topic": "oscillation-command-topic",
                "speed_state_topic": "speed-state-topic",
                "speed_command_topic": "speed-command-topic",
                "optimistic": True,
            }
        },
    )

    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_turn_on(opp, "fan.test")
    mqtt_mock.async_publish.assert_called_once_with("command-topic", "ON", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_ON
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_turn_off(opp, "fan.test")
    mqtt_mock.async_publish.assert_called_once_with("command-topic", "OFF", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_oscillate(opp, "fan.test", True)
    mqtt_mock.async_publish.assert_called_once_with(
        "oscillation-command-topic", "oscillate_on", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_oscillate(opp, "fan.test", False)
    mqtt_mock.async_publish.assert_called_once_with(
        "oscillation-command-topic", "oscillate_off", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_LOW)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "low", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_MEDIUM)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "medium", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_HIGH)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "high", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_set_speed(opp, "fan.test", fan.SPEED_OFF)
    mqtt_mock.async_publish.assert_called_once_with(
        "speed-command-topic", "off", 0, False
    )
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("fan.test")
    assert state.state is STATE_OFF
    assert state.attributes.get(ATTR_ASSUMED_STATE)


async def test_default_availability_payload(opp, mqtt_mock):
    """Test the availability payload."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "availability_topic": "availability_topic",
            }
        },
    )

    state = opp.states.get("fan.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability_topic", "online")

    state = opp.states.get("fan.test")
    assert state.state is not STATE_UNAVAILABLE
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "availability_topic", "offline")

    state = opp.states.get("fan.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "state-topic", "1")

    state = opp.states.get("fan.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability_topic", "online")

    state = opp.states.get("fan.test")
    assert state.state is not STATE_UNAVAILABLE


async def test_custom_availability_payload(opp, mqtt_mock):
    """Test the availability payload."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "availability_topic": "availability_topic",
                "payload_available": "good",
                "payload_not_available": "nogood",
            }
        },
    )

    state = opp.states.get("fan.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability_topic", "good")

    state = opp.states.get("fan.test")
    assert state.state is not STATE_UNAVAILABLE
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "availability_topic", "nogood")

    state = opp.states.get("fan.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "state-topic", "1")

    state = opp.states.get("fan.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability_topic", "good")

    state = opp.states.get("fan.test")
    assert state.state is not STATE_UNAVAILABLE


async def test_discovery_removal_fan(opp, mqtt_mock, caplog):
    """Test removal of discovered fan."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data = '{ "name": "Beer",' '  "command_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data)
    await opp.async_block_till_done()
    state = opp.states.get("fan.beer")
    assert state is not None
    assert state.name == "Beer"
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", "")
    await opp.async_block_till_done()
    state = opp.states.get("fan.beer")
    assert state is None


async def test_discovery_update_fan(opp, mqtt_mock, caplog):
    """Test update of discovered fan."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data1 = '{ "name": "Beer",' '  "command_topic": "test_topic" }'
    data2 = '{ "name": "Milk",' '  "command_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("fan.beer")
    assert state is not None
    assert state.name == "Beer"

    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("fan.beer")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("fan.milk")
    assert state is None


async def test_discovery_broken(opp, mqtt_mock, caplog):
    """Test handling of bad discovery message."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk",' '  "command_topic": "test_topic" }'

    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("fan.beer")
    assert state is None

    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("fan.milk")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("fan.beer")
    assert state is None


async def test_setting_attribute_via_mqtt_json_message(opp, mqtt_mock):
    """Test the setting of attribute via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '{ "val": "100" }')
    state = opp.states.get("fan.test")

    assert state.attributes.get("val") == "100"


async def test_update_with_json_attrs_not_dict(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '[ "list", "of", "things"]')
    state = opp.states.get("fan.test")

    assert state.attributes.get("val") is None
    assert "JSON result was not a dictionary" in caplog.text


async def test_update_with_json_attrs_bad_JSON(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", "This is not JSON")

    state = opp.states.get("fan.test")
    assert state.attributes.get("val") is None
    assert "Erroneous JSON: This is not JSON" in caplog.text


async def test_discovery_update_attr(opp, mqtt_mock, caplog):
    """Test update of discovered MQTTAttributes."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data1 = (
        '{ "name": "Beer",'
        '  "command_topic": "test_topic",'
        '  "json_attributes_topic": "attr-topic1" }'
    )
    data2 = (
        '{ "name": "Beer",'
        '  "command_topic": "test_topic",'
        '  "json_attributes_topic": "attr-topic2" }'
    )
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data1)
    await opp.async_block_till_done()
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "100" }')
    state = opp.states.get("fan.beer")
    assert state.attributes.get("val") == "100"

    # Change json_attributes_topic
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data2)
    await opp.async_block_till_done()

    # Verify we are no longer subscribing to the old topic
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "50" }')
    state = opp.states.get("fan.beer")
    assert state.attributes.get("val") == "100"

    # Verify we are subscribing to the new topic
    async_fire_mqtt_message(opp, "attr-topic2", '{ "val": "75" }')
    state = opp.states.get("fan.beer")
    assert state.attributes.get("val") == "75"


async def test_unique_id(opp):
    """Test unique_id option only creates one fan per id."""
    await async_mock_mqtt_component(opp)
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "Test 1",
                    "state_topic": "test-topic",
                    "command_topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
                {
                    "platform": "mqtt",
                    "name": "Test 2",
                    "state_topic": "test-topic",
                    "command_topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
            ]
        },
    )

    async_fire_mqtt_message(opp, "test-topic", "payload")

    assert len(opp.states.async_entity_ids(fan.DOMAIN)) == 1


async def test_entity_device_info_with_identifier(opp, mqtt_mock):
    """Test MQTT fan device registry integration."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_opp(opp)
    await async_start(opp, "openpeerpower", {}, entry)
    registry = await opp.helpers.device_registry.async_get_registry()

    data = json.dumps(
        {
            "platform": "mqtt",
            "name": "Test 1",
            "state_topic": "test-topic",
            "command_topic": "test-command-topic",
            "device": {
                "identifiers": ["helloworld"],
                "connections": [["mac", "02:5b:26:a8:dc:12"]],
                "manufacturer": "Whatever",
                "name": "Beer",
                "model": "Glass",
                "sw_version": "0.1-beta",
            },
            "unique_id": "veryunique",
        }
    )
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.identifiers == {("mqtt", "helloworld")}
    assert device.connections == {("mac", "02:5b:26:a8:dc:12")}
    assert device.manufacturer == "Whatever"
    assert device.name == "Beer"
    assert device.model == "Glass"
    assert device.sw_version == "0.1-beta"


async def test_entity_device_info_update(opp, mqtt_mock):
    """Test device registry update."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_opp(opp)
    await async_start(opp, "openpeerpower", {}, entry)
    registry = await opp.helpers.device_registry.async_get_registry()

    config = {
        "platform": "mqtt",
        "name": "Test 1",
        "state_topic": "test-topic",
        "command_topic": "test-command-topic",
        "device": {
            "identifiers": ["helloworld"],
            "connections": [["mac", "02:5b:26:a8:dc:12"]],
            "manufacturer": "Whatever",
            "name": "Beer",
            "model": "Glass",
            "sw_version": "0.1-beta",
        },
        "unique_id": "veryunique",
    }

    data = json.dumps(config)
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(opp, "openpeerpower/fan/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Milk"


async def test_entity_id_update(opp, mqtt_mock):
    """Test MQTT subscriptions are managed when entity_id is updated."""
    registry = mock_registry(opp, {})
    mock_mqtt = await async_mock_mqtt_component(opp)
    assert await async_setup_component(
        opp,
        fan.DOMAIN,
        {
            fan.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "beer",
                    "state_topic": "test-topic",
                    "command_topic": "command-topic",
                    "availability_topic": "avty-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                }
            ]
        },
    )

    state = opp.states.get("fan.beer")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.reset_mock()

    registry.async_update_entity("fan.beer", new_entity_id="fan.milk")
    await opp.async_block_till_done()

    state = opp.states.get("fan.beer")
    assert state is None

    state = opp.states.get("fan.milk")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
