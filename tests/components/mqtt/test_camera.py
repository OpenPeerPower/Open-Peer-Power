"""The tests for mqtt camera component."""
import json
from unittest.mock import ANY

from openpeerpower.components import camera, mqtt
from openpeerpower.components.mqtt.discovery import async_start
from openpeerpower.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_mqtt_component,
    mock_registry,
)


async def test_run_camera_setup(opp, aiohttp_client):
    """Test that it fetches the given payload."""
    topic = "test/camera"
    await async_mock_mqtt_component(opp)
    await async_setup_component(
        opp,
        "camera",
        {"camera": {"platform": "mqtt", "topic": topic, "name": "Test Camera"}},
    )

    url = opp.states.get("camera.test_camera").attributes["entity_picture"]

    async_fire_mqtt_message(opp, topic, "beer")

    client = await aiohttp_client(opp.http.app)
    resp = await client.get(url)
    assert resp.status == 200
    body = await resp.text()
    assert body == "beer"


async def test_unique_id(opp):
    """Test unique id option only creates one camera per unique_id."""
    await async_mock_mqtt_component(opp)
    await async_setup_component(
        opp,
        "camera",
        {
            "camera": [
                {
                    "platform": "mqtt",
                    "name": "Test Camera 1",
                    "topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
                {
                    "platform": "mqtt",
                    "name": "Test Camera 2",
                    "topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                },
            ]
        },
    )

    async_fire_mqtt_message(opp, "test-topic", "payload")
    assert len(opp.states.async_all()) == 1


async def test_discovery_removal_camera(opp, mqtt_mock, caplog):
    """Test removal of discovered camera."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data = '{ "name": "Beer",' '  "topic": "test_topic"}'

    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data)
    await opp.async_block_till_done()

    state = opp.states.get("camera.beer")
    assert state is not None
    assert state.name == "Beer"

    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", "")
    await opp.async_block_till_done()

    state = opp.states.get("camera.beer")
    assert state is None


async def test_discovery_update_camera(opp, mqtt_mock, caplog):
    """Test update of discovered camera."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data1 = '{ "name": "Beer",' '  "topic": "test_topic"}'
    data2 = '{ "name": "Milk",' '  "topic": "test_topic"}'

    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("camera.beer")
    assert state is not None
    assert state.name == "Beer"

    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("camera.beer")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("camera.milk")
    assert state is None


async def test_discovery_broken(opp, mqtt_mock, caplog):
    """Test handling of bad discovery message."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data1 = '{ "name": "Beer" }'
    data2 = '{ "name": "Milk",' '  "topic": "test_topic"}'

    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("camera.beer")
    assert state is None

    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("camera.milk")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("camera.beer")
    assert state is None


async def test_entity_id_update(opp, mqtt_mock):
    """Test MQTT subscriptions are managed when entity_id is updated."""
    registry = mock_registry(opp, {})
    mock_mqtt = await async_mock_mqtt_component(opp)
    assert await async_setup_component(
        opp,
        camera.DOMAIN,
        {
            camera.DOMAIN: [
                {
                    "platform": "mqtt",
                    "name": "beer",
                    "topic": "test-topic",
                    "unique_id": "TOTALLY_UNIQUE",
                }
            ]
        },
    )

    state = opp.states.get("camera.beer")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 1
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, None)
    mock_mqtt.async_subscribe.reset_mock()

    registry.async_update_entity("camera.beer", new_entity_id="camera.milk")
    await opp.async_block_till_done()

    state = opp.states.get("camera.beer")
    assert state is None

    state = opp.states.get("camera.milk")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 1
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, None)


async def test_entity_device_info_with_identifier(opp, mqtt_mock):
    """Test MQTT camera device registry integration."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    entry.add_to_opp(opp)
    await async_start(opp, "openpeerpower", {}, entry)
    registry = await opp.helpers.device_registry.async_get_registry()

    data = json.dumps(
        {
            "platform": "mqtt",
            "name": "Test 1",
            "topic": "test-topic",
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
    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data)
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
        "topic": "test-topic",
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
    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(opp, "openpeerpower/camera/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Milk"
