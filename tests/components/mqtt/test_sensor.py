"""The tests for the MQTT sensor platform."""
from datetime import datetime, timedelta
import json
from unittest.mock import ANY, patch

from openpeerpower.components import mqtt
from openpeerpower.components.mqtt.discovery import async_start
import openpeerpower.components.sensor as sensor
from openpeerpower.const import EVENT_STATE_CHANGED, STATE_UNAVAILABLE
import openpeerpower.core as op
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_fire_time_changed,
    async_mock_mqtt_component,
    mock_registry,
)


async def test_setting_sensor_value_via_mqtt_message(opp, mqtt_mock):
    """Test the setting of the value via MQTT."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
            }
        },
    )

    async_fire_mqtt_message(opp, "test-topic", "100")
    state = opp.states.get("sensor.test")

    assert state.state == "100"
    assert state.attributes.get("unit_of_measurement") == "fav unit"


async def test_setting_sensor_value_expires(opp, mqtt_mock, caplog):
    """Test the expiration of the value."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "expire_after": "4",
                "force_update": True,
            }
        },
    )

    state = opp.states.get("sensor.test")
    assert state.state == "unknown"

    now = datetime(2017, 1, 1, 1, tzinfo=dt_util.UTC)
    with patch(("openpeerpower.helpers.event.dt_util.utcnow"), return_value=now):
        async_fire_time_changed(opp, now)
        async_fire_mqtt_message(opp, "test-topic", "100")
        await opp.async_block_till_done()

    # Value was set correctly.
    state = opp.states.get("sensor.test")
    assert state.state == "100"

    # Time jump +3s
    now = now + timedelta(seconds=3)
    async_fire_time_changed(opp, now)
    await opp.async_block_till_done()

    # Value is not yet expired
    state = opp.states.get("sensor.test")
    assert state.state == "100"

    # Next message resets timer
    with patch(("openpeerpower.helpers.event.dt_util.utcnow"), return_value=now):
        async_fire_time_changed(opp, now)
        async_fire_mqtt_message(opp, "test-topic", "101")
        await opp.async_block_till_done()

    # Value was updated correctly.
    state = opp.states.get("sensor.test")
    assert state.state == "101"

    # Time jump +3s
    now = now + timedelta(seconds=3)
    async_fire_time_changed(opp, now)
    await opp.async_block_till_done()

    # Value is not yet expired
    state = opp.states.get("sensor.test")
    assert state.state == "101"

    # Time jump +2s
    now = now + timedelta(seconds=2)
    async_fire_time_changed(opp, now)
    await opp.async_block_till_done()

    # Value is expired now
    state = opp.states.get("sensor.test")
    assert state.state == "unknown"


async def test_setting_sensor_value_via_mqtt_json_message(opp, mqtt_mock):
    """Test the setting of the value via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "value_template": "{{ value_json.val }}",
            }
        },
    )

    async_fire_mqtt_message(opp, "test-topic", '{ "val": "100" }')
    state = opp.states.get("sensor.test")

    assert state.state == "100"


async def test_force_update_disabled(opp, mqtt_mock):
    """Test force update option."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
            }
        },
    )

    events = []

    @op.callback
    def callback(event):
        events.append(event)

    opp.bus.async_listen(EVENT_STATE_CHANGED, callback)

    async_fire_mqtt_message(opp, "test-topic", "100")
    await opp.async_block_till_done()
    assert len(events) == 1

    async_fire_mqtt_message(opp, "test-topic", "100")
    await opp.async_block_till_done()
    assert len(events) == 1


async def test_force_update_enabled(opp, mqtt_mock):
    """Test force update option."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "force_update": True,
            }
        },
    )

    events = []

    @op.callback
    def callback(event):
        events.append(event)

    opp.bus.async_listen(EVENT_STATE_CHANGED, callback)

    async_fire_mqtt_message(opp, "test-topic", "100")
    await opp.async_block_till_done()
    assert len(events) == 1

    async_fire_mqtt_message(opp, "test-topic", "100")
    await opp.async_block_till_done()
    assert len(events) == 2


async def test_default_availability_payload(opp, mqtt_mock):
    """Test availability by default payload with defined topic."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "availability_topic": "availability-topic",
            }
        },
    )

    state = opp.states.get("sensor.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "online")

    state = opp.states.get("sensor.test")
    assert state.state != STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "offline")

    state = opp.states.get("sensor.test")
    assert state.state == STATE_UNAVAILABLE


async def test_custom_availability_payload(opp, mqtt_mock):
    """Test availability by custom payload with defined topic."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "availability_topic": "availability-topic",
                "payload_available": "good",
                "payload_not_available": "nogood",
            }
        },
    )

    state = opp.states.get("sensor.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "good")

    state = opp.states.get("sensor.test")
    assert state.state != STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "nogood")

    state = opp.states.get("sensor.test")
    assert state.state == STATE_UNAVAILABLE


async def test_setting_sensor_attribute_via_legacy_mqtt_json_message(opp, mqtt_mock):
    """Test the setting of attribute via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "json_attributes_topic": "test-attributes-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "test-attributes-topic", '{ "val": "100" }')
    state = opp.states.get("sensor.test")

    assert state.attributes.get("val") == "100"


async def test_update_with_legacy_json_attrs_not_dict(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "json_attributes_topic": "test-attributes-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "test-attributes-topic", '[ "list", "of", "things"]')
    state = opp.states.get("sensor.test")

    assert state.attributes.get("val") is None
    assert "JSON result was not a dictionary" in caplog.text


async def test_update_with_legacy_json_attrs_bad_JSON(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "json_attributes_topic": "test-attributes-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "test-attributes-topic", "This is not JSON")

    state = opp.states.get("sensor.test")
    assert state.attributes.get("val") is None
    assert "Erroneous JSON: This is not JSON" in caplog.text


async def test_update_with_legacy_json_attrs_and_template(opp, mqtt_mock):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "unit_of_measurement": "fav unit",
                "value_template": "{{ value_json.val }}",
                "json_attributes": "val",
            }
        },
    )

    async_fire_mqtt_message(opp, "test-topic", '{ "val": "100" }')
    state = opp.states.get("sensor.test")

    assert state.attributes.get("val") == "100"
    assert state.state == "100"


async def test_invalid_device_class(opp, mqtt_mock):
    """Test device_class option with invalid value."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "device_class": "foobarnotreal",
            }
        },
    )

    state = opp.states.get("sensor.test")
    assert state is None


async def test_valid_device_class(opp, mqtt_mock):
    """Test device_class option with valid values."""
    assert await async_setup_component(
        opp,
        "sensor",
        {
            "sensor": [
                {
                    "platform": "mqtt",
                    "name": "Test 1",
                    "state_topic": "test-topic",
                    "device_class": "temperature",
                },
                {"platform": "mqtt", "name": "Test 2", "state_topic": "test-topic"},
            ]
        },
    )
    await opp.async_block_till_done()

    state = opp.states.get("sensor.test_1")
    assert state.attributes["device_class"] == "temperature"
    state = opp.states.get("sensor.test_2")
    assert "device_class" not in state.attributes


async def test_setting_attribute_via_mqtt_json_message(opp, mqtt_mock):
    """Test the setting of attribute via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '{ "val": "100" }')
    state = opp.states.get("sensor.test")

    assert state.attributes.get("val") == "100"


async def test_setting_attribute_with_template(opp, mqtt_mock):
    """Test the setting of attribute via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
                "json_attributes_template": "{{ value_json['Timer1'] | tojson }}",
            }
        },
    )

    async_fire_mqtt_message(
        opp, "attr-topic", json.dumps({"Timer1": {"Arm": 0, "Time": "22:18"}})
    )
    state = opp.states.get("sensor.test")

    assert state.attributes.get("Arm") == 0
    assert state.attributes.get("Time") == "22:18"


async def test_update_with_json_attrs_not_dict(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '[ "list", "of", "things"]')
    state = opp.states.get("sensor.test")

    assert state.attributes.get("val") is None
    assert "JSON result was not a dictionary" in caplog.text


async def test_update_with_json_attrs_bad_JSON(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", "This is not JSON")

    state = opp.states.get("sensor.test")
    assert state.attributes.get("val") is None
    assert "Erroneous JSON: This is not JSON" in caplog.text


async def test_discovery_update_attr(opp, mqtt_mock, caplog):
    """Test update of discovered MQTTAttributes."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data1 = (
        '{ "name": "Beer",'
        '  "state_topic": "test_topic",'
        '  "json_attributes_topic": "attr-topic1" }'
    )
    data2 = (
        '{ "name": "Beer",'
        '  "state_topic": "test_topic",'
        '  "json_attributes_topic": "attr-topic2" }'
    )
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data1)
    await opp.async_block_till_done()
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "100" }')
    state = opp.states.get("sensor.beer")
    assert state.attributes.get("val") == "100"

    # Change json_attributes_topic
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data2)
    await opp.async_block_till_done()

    # Verify we are no longer subscribing to the old topic
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "50" }')
    state = opp.states.get("sensor.beer")
    assert state.attributes.get("val") == "100"

    # Verify we are subscribing to the new topic
    async_fire_mqtt_message(opp, "attr-topic2", '{ "val": "75" }')
    state = opp.states.get("sensor.beer")
    assert state.attributes.get("val") == "75"


async def test_unique_id(opp):
    """Test unique id option only creates one sensor per unique_id."""
    await async_mock_mqtt_component(opp)
    assert await async_setup_component(
        opp,
        sensor.DOMAIN,
        {
            sensor.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "Test 1",
                    "state_topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
                {
                    "platform": "mqtt",
                    "name": "Test 2",
                    "state_topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
            ]
        },
    )

    async_fire_mqtt_message(opp, "test-topic", "payload")

    assert len(opp.states.async_all()) == 1


async def test_discovery_removal_sensor(opp, mqtt_mock, caplog):
    """Test removal of discovered sensor."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data = '{ "name": "Beer",' '  "state_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data)
    await opp.async_block_till_done()
    state = opp.states.get("sensor.beer")
    assert state is not None
    assert state.name == "Beer"
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", "")
    await opp.async_block_till_done()
    state = opp.states.get("sensor.beer")
    assert state is None


async def test_discovery_update_sensor(opp, mqtt_mock, caplog):
    """Test update of discovered sensor."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data1 = '{ "name": "Beer",' '  "state_topic": "test_topic" }'
    data2 = '{ "name": "Milk",' '  "state_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("sensor.beer")
    assert state is not None
    assert state.name == "Beer"

    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("sensor.beer")
    assert state is not None
    assert state.name == "Milk"

    state = opp.states.get("sensor.milk")
    assert state is None


async def test_discovery_broken(opp, mqtt_mock, caplog):
    """Test handling of bad discovery message."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data1 = '{ "name": "Beer",' '  "state_topic": "test_topic#" }'
    data2 = '{ "name": "Milk",' '  "state_topic": "test_topic" }'

    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("sensor.beer")
    assert state is None

    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("sensor.milk")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("sensor.beer")
    assert state is None


async def test_entity_device_info_with_identifier(opp, mqtt_mock):
    """Test MQTT sensor device registry integration."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_opp(opp)
    await async_start(opp, "openpeerpower", {}, entry)
    registry = await opp.helpers.device_registry.async_get_registry()

    data = json.dumps(
        {
            "platform": "mqtt",
            "name": "Test 1",
            "state_topic": "test-topic",
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
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data)
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
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data)
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
        sensor.DOMAIN,
        {
            sensor.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "beer",
                    "state_topic": "test-topic",
                    "availability_topic": "avty-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                }
            ]
        },
    )

    state = opp.states.get("sensor.beer")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.reset_mock()

    registry.async_update_entity("sensor.beer", new_entity_id="sensor.milk")
    await opp.async_block_till_done()

    state = opp.states.get("sensor.beer")
    assert state is None

    state = opp.states.get("sensor.milk")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")


async def test_entity_device_info_with_hub(opp, mqtt_mock):
    """Test MQTT sensor device registry integration."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_opp(opp)
    await async_start(opp, "openpeerpower", {}, entry)

    registry = await opp.helpers.device_registry.async_get_registry()
    hub = registry.async_get_or_create(
        config_entry_id="123",
        connections=set(),
        identifiers={("mqtt", "hub-id")},
        manufacturer="manufacturer",
        model="hub",
    )

    data = json.dumps(
        {
            "platform": "mqtt",
            "name": "Test 1",
            "state_topic": "test-topic",
            "device": {"identifiers": ["helloworld"], "via_device": "hub-id"},
            "unique_id": "veryunique",
        }
    )
    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.via_device_id == hub.id
