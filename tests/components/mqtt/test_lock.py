"""The tests for the MQTT lock platform."""
import json
from unittest.mock import ANY

from openpeerpower.components import lock, mqtt
from openpeerpower.components.mqtt.discovery import async_start
from openpeerpower.const import (
    ATTR_ASSUMED_STATE,
    STATE_LOCKED,
    STATE_UNAVAILABLE,
    STATE_UNLOCKED,
)
from openpeerpower.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_mqtt_component,
    mock_registry,
)
from tests.components.lock import common


async def test_controlling_state_via_topic(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "LOCKED",
                "state_unlocked": "UNLOCKED",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "state-topic", "LOCKED")

    state = opp.states.get("lock.test")
    assert state.state is STATE_LOCKED

    async_fire_mqtt_message(opp, "state-topic", "UNLOCKED")

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED


async def test_controlling_non_default_state_via_topic(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "closed",
                "state_unlocked": "open",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "state-topic", "closed")

    state = opp.states.get("lock.test")
    assert state.state is STATE_LOCKED

    async_fire_mqtt_message(opp, "state-topic", "open")

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED


async def test_controlling_state_via_topic_and_json_message(opp, mqtt_mock):
    """Test the controlling state via topic and JSON message."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "LOCKED",
                "state_unlocked": "UNLOCKED",
                "value_template": "{{ value_json.val }}",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED

    async_fire_mqtt_message(opp, "state-topic", '{"val":"LOCKED"}')

    state = opp.states.get("lock.test")
    assert state.state is STATE_LOCKED

    async_fire_mqtt_message(opp, "state-topic", '{"val":"UNLOCKED"}')

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED


async def test_controlling_non_default_state_via_topic_and_json_message(
    opp, mqtt_mock
):
    """Test the controlling state via topic and JSON message."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "closed",
                "state_unlocked": "open",
                "value_template": "{{ value_json.val }}",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED

    async_fire_mqtt_message(opp, "state-topic", '{"val":"closed"}')

    state = opp.states.get("lock.test")
    assert state.state is STATE_LOCKED

    async_fire_mqtt_message(opp, "state-topic", '{"val":"open"}')

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED


async def test_sending_mqtt_commands_and_optimistic(opp, mqtt_mock):
    """Test optimistic mode without state topic."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "LOCKED",
                "state_unlocked": "UNLOCKED",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_lock(opp, "lock.test")

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "LOCK", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("lock.test")
    assert state.state is STATE_LOCKED
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_unlock(opp, "lock.test")

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "UNLOCK", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED
    assert state.attributes.get(ATTR_ASSUMED_STATE)


async def test_sending_mqtt_commands_and_explicit_optimistic(opp, mqtt_mock):
    """Test optimistic mode without state topic."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "LOCKED",
                "state_unlocked": "UNLOCKED",
                "optimistic": True,
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_lock(opp, "lock.test")

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "LOCK", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("lock.test")
    assert state.state is STATE_LOCKED
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await common.async_unlock(opp, "lock.test")

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "UNLOCK", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("lock.test")
    assert state.state is STATE_UNLOCKED
    assert state.attributes.get(ATTR_ASSUMED_STATE)


async def test_default_availability_payload(opp, mqtt_mock):
    """Test availability by default payload with defined topic."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "availability_topic": "availability-topic",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "online")

    state = opp.states.get("lock.test")
    assert state.state is not STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "offline")

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNAVAILABLE


async def test_custom_availability_payload(opp, mqtt_mock):
    """Test availability by custom payload with defined topic."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "payload_lock": "LOCK",
                "payload_unlock": "UNLOCK",
                "state_locked": "LOCKED",
                "state_unlocked": "UNLOCKED",
                "availability_topic": "availability-topic",
                "payload_available": "good",
                "payload_not_available": "nogood",
            }
        },
    )

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "good")

    state = opp.states.get("lock.test")
    assert state.state is not STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "nogood")

    state = opp.states.get("lock.test")
    assert state.state is STATE_UNAVAILABLE


async def test_setting_attribute_via_mqtt_json_message(opp, mqtt_mock):
    """Test the setting of attribute via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '{ "val": "100" }')
    state = opp.states.get("lock.test")

    assert state.attributes.get("val") == "100"


async def test_update_with_json_attrs_not_dict(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '[ "list", "of", "things"]')
    state = opp.states.get("lock.test")

    assert state.attributes.get("val") is None
    assert "JSON result was not a dictionary" in caplog.text


async def test_update_with_json_attrs_bad_JSON(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", "This is not JSON")

    state = opp.states.get("lock.test")
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
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data1)
    await opp.async_block_till_done()
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "100" }')
    state = opp.states.get("lock.beer")
    assert state.attributes.get("val") == "100"

    # Change json_attributes_topic
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data2)
    await opp.async_block_till_done()

    # Verify we are no longer subscribing to the old topic
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "50" }')
    state = opp.states.get("lock.beer")
    assert state.attributes.get("val") == "100"

    # Verify we are subscribing to the new topic
    async_fire_mqtt_message(opp, "attr-topic2", '{ "val": "75" }')
    state = opp.states.get("lock.beer")
    assert state.attributes.get("val") == "75"


async def test_unique_id(opp):
    """Test unique id option only creates one light per unique_id."""
    await async_mock_mqtt_component(opp)
    assert await async_setup_component(
        opp,
        lock.DOMAIN,
        {
            lock.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "Test 1",
                    "state_topic": "test-topic",
                    "command_topic": "test_topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
                {
                    "platform": "mqtt",
                    "name": "Test 2",
                    "state_topic": "test-topic",
                    "command_topic": "test_topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
            ]
        },
    )
    async_fire_mqtt_message(opp, "test-topic", "payload")
    assert len(opp.states.async_entity_ids(lock.DOMAIN)) == 1


async def test_discovery_removal_lock(opp, mqtt_mock, caplog):
    """Test removal of discovered lock."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data = '{ "name": "Beer",' '  "command_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data)
    await opp.async_block_till_done()
    state = opp.states.get("lock.beer")
    assert state is not None
    assert state.name == "Beer"
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", "")
    await opp.async_block_till_done()
    state = opp.states.get("lock.beer")
    assert state is None


async def test_discovery_broken(opp, mqtt_mock, caplog):
    """Test handling of bad discovery message."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk",' '  "command_topic": "test_topic" }'

    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("lock.beer")
    assert state is None

    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("lock.milk")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("lock.beer")
    assert state is None


async def test_discovery_update_lock(opp, mqtt_mock, caplog):
    """Test update of discovered lock."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data1 = (
        '{ "name": "Beer",'
        '  "state_topic": "test_topic",'
        '  "command_topic": "command_topic",'
        '  "availability_topic": "availability_topic1" }'
    )
    data2 = (
        '{ "name": "Milk",'
        '  "state_topic": "test_topic2",'
        '  "command_topic": "command_topic",'
        '  "availability_topic": "availability_topic2" }'
    )
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data1)
    await opp.async_block_till_done()
    state = opp.states.get("lock.beer")
    assert state is not None
    assert state.name == "Beer"
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data2)
    await opp.async_block_till_done()
    state = opp.states.get("lock.beer")
    assert state is not None
    assert state.name == "Milk"

    state = opp.states.get("lock.milk")
    assert state is None


async def test_entity_device_info_with_identifier(opp, mqtt_mock):
    """Test MQTT lock device registry integration."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_opp(opp)
    await async_start(opp, "openpeerpower", {}, entry)
    registry = await opp.helpers.device_registry.async_get_registry()

    data = json.dumps(
        {
            "platform": "mqtt",
            "name": "Test 1",
            "state_topic": "test-topic",
            "command_topic": "test-topic",
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
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data)
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
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(opp, "openpeerpower/lock/bla/config", data)
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
        lock.DOMAIN,
        {
            lock.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "beer",
                    "state_topic": "test-topic",
                    "command_topic": "test-topic",
                    "availability_topic": "avty-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                }
            ]
        },
    )

    state = opp.states.get("lock.beer")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.reset_mock()

    registry.async_update_entity("lock.beer", new_entity_id="lock.milk")
    await opp.async_block_till_done()

    state = opp.states.get("lock.beer")
    assert state is None

    state = opp.states.get("lock.milk")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
