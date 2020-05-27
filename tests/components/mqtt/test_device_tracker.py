"""The tests for the MQTT device tracker platform."""
from asynctest import patch
import pytest

from openpeerpower.components import device_tracker
from openpeerpower.components.device_tracker.const import (
    ENTITY_ID_FORMAT,
    SOURCE_TYPE_BLUETOOTH,
)
from openpeerpower.const import CONF_PLATFORM, STATE_HOME, STATE_NOT_HOME
from openpeerpower.setup import async_setup_component

from tests.common import async_fire_mqtt_message


@pytest.fixture(autouse=True)
def setup_comp(opp, mqtt_mock):
    """Set up mqtt component."""
    pass


async def test_ensure_device_tracker_platform_validation(opp):
    """Test if platform validation was done."""

    async def mock_setup_scanner(opp, config, see, discovery_info=None):
        """Check that Qos was added by validation."""
        assert "qos" in config

    with patch(
        "openpeerpower.components.mqtt.device_tracker.async_setup_scanner",
        autospec=True,
        side_effect=mock_setup_scanner,
    ) as mock_sp:

        dev_id = "paulus"
        topic = "/location/paulus"
        assert await async_setup_component(
            opp,
            device_tracker.DOMAIN,
            {
                device_tracker.DOMAIN: {
                    CONF_PLATFORM: "mqtt",
                    "devices": {dev_id: topic},
                }
            },
        )
        assert mock_sp.call_count == 1


async def test_new_message(opp, mock_device_tracker_conf):
    """Test new message."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    topic = "/location/paulus"
    location = "work"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {device_tracker.DOMAIN: {CONF_PLATFORM: "mqtt", "devices": {dev_id: topic}}},
    )
    async_fire_mqtt_message(opp, topic, location)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).state == location


async def test_single_level_wildcard_topic(opp, mock_device_tracker_conf):
    """Test single level wildcard topic."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    subscription = "/location/+/paulus"
    topic = "/location/room/paulus"
    location = "work"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: subscription},
            }
        },
    )
    async_fire_mqtt_message(opp, topic, location)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).state == location


async def test_multi_level_wildcard_topic(opp, mock_device_tracker_conf):
    """Test multi level wildcard topic."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    subscription = "/location/#"
    topic = "/location/room/paulus"
    location = "work"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: subscription},
            }
        },
    )
    async_fire_mqtt_message(opp, topic, location)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).state == location


async def test_single_level_wildcard_topic_not_matching(opp, mock_device_tracker_conf):
    """Test not matching single level wildcard topic."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    subscription = "/location/+/paulus"
    topic = "/location/paulus"
    location = "work"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: subscription},
            }
        },
    )
    async_fire_mqtt_message(opp, topic, location)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id) is None


async def test_multi_level_wildcard_topic_not_matching(opp, mock_device_tracker_conf):
    """Test not matching multi level wildcard topic."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    subscription = "/location/#"
    topic = "/somewhere/room/paulus"
    location = "work"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: subscription},
            }
        },
    )
    async_fire_mqtt_message(opp, topic, location)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id) is None


async def test_matching_custom_payload_for_home_and_not_home(
    opp, mock_device_tracker_conf
):
    """Test custom payload_home sets state to home and custom payload_not_home sets state to not_home."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    topic = "/location/paulus"
    payload_home = "present"
    payload_not_home = "not present"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: topic},
                "payload_home": payload_home,
                "payload_not_home": payload_not_home,
            }
        },
    )
    async_fire_mqtt_message(opp, topic, payload_home)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).state == STATE_HOME

    async_fire_mqtt_message(opp, topic, payload_not_home)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).state == STATE_NOT_HOME


async def test_not_matching_custom_payload_for_home_and_not_home(
    opp, mock_device_tracker_conf
):
    """Test not matching payload does not set state to home or not_home."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    topic = "/location/paulus"
    payload_home = "present"
    payload_not_home = "not present"
    payload_not_matching = "test"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: topic},
                "payload_home": payload_home,
                "payload_not_home": payload_not_home,
            }
        },
    )
    async_fire_mqtt_message(opp, topic, payload_not_matching)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).state != STATE_HOME
    assert opp.states.get(entity_id).state != STATE_NOT_HOME


async def test_matching_source_type(opp, mock_device_tracker_conf):
    """Test setting source type."""
    dev_id = "paulus"
    entity_id = ENTITY_ID_FORMAT.format(dev_id)
    topic = "/location/paulus"
    source_type = SOURCE_TYPE_BLUETOOTH
    location = "work"

    opp.config.components = set(["mqtt", "zone"])
    assert await async_setup_component(
        opp,
        device_tracker.DOMAIN,
        {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: "mqtt",
                "devices": {dev_id: topic},
                "source_type": source_type,
            }
        },
    )

    async_fire_mqtt_message(opp, topic, location)
    await opp.async_block_till_done()
    assert opp.states.get(entity_id).attributes["source_type"] == SOURCE_TYPE_BLUETOOTH