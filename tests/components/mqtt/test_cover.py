"""The tests for the MQTT cover platform."""
import json
from unittest.mock import ANY

from openpeerpower.components import cover, mqtt
from openpeerpower.components.cover import ATTR_POSITION, ATTR_TILT_POSITION
from openpeerpower.components.mqtt.cover import MqttCover
from openpeerpower.components.mqtt.discovery import async_start
from openpeerpower.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_STOP_COVER,
    SERVICE_TOGGLE,
    SERVICE_TOGGLE_COVER_TILT,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from openpeerpower.setup import async_setup_component

from tests.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
    async_mock_mqtt_component,
    mock_registry,
)


async def test_state_via_state_topic(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "state-topic", STATE_CLOSED)

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED

    async_fire_mqtt_message(opp, "state-topic", STATE_OPEN)

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN


async def test_opening_and_closing_state_via_custom_state_payload(opp, mqtt_mock):
    """Test the controlling opening and closing state via a custom payload."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "state_opening": "34",
                "state_closing": "--43",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "state-topic", "34")

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPENING

    async_fire_mqtt_message(opp, "state-topic", "--43")

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSING

    async_fire_mqtt_message(opp, "state-topic", STATE_CLOSED)

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED


async def test_open_closed_state_from_position_optimistic(opp, mqtt_mock):
    """Test the state after setting the position using optimistic mode."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "position-topic",
                "set_position_topic": "set-position-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "optimistic": True,
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: "cover.test", ATTR_POSITION: 0},
        blocking=True,
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: "cover.test", ATTR_POSITION: 100},
        blocking=True,
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN
    assert state.attributes.get(ATTR_ASSUMED_STATE)


async def test_position_via_position_topic(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "get-position-topic",
                "position_open": 100,
                "position_closed": 0,
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN
    assert not state.attributes.get(ATTR_ASSUMED_STATE)

    async_fire_mqtt_message(opp, "get-position-topic", "0")

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED

    async_fire_mqtt_message(opp, "get-position-topic", "100")

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN


async def test_state_via_template(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "value_template": "\
                {% if (value | multiply(0.01) | int) == 0  %}\
                  closed\
                {% else %}\
                  open\
                {% endif %}",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(opp, "state-topic", "10000")

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN

    async_fire_mqtt_message(opp, "state-topic", "99")

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED


async def test_position_via_template(opp, mqtt_mock):
    """Test the controlling state via topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "get-position-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "value_template": "{{ (value | multiply(0.01)) | int }}",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN

    async_fire_mqtt_message(opp, "get-position-topic", "10000")

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN

    async_fire_mqtt_message(opp, "get-position-topic", "5000")

    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN

    async_fire_mqtt_message(opp, "get-position-topic", "99")

    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED


async def test_optimistic_state_change(opp, mqtt_mock):
    """Test changing state optimistically."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "command-topic",
                "qos": 0,
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ASSUMED_STATE)

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "OPEN", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("cover.test")
    assert state.state == STATE_OPEN

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "CLOSE", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("cover.test")
    assert STATE_CLOSED == state.state

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "OPEN", 0, False)
    mqtt_mock.async_publish.reset_mock()
    state = opp.states.get("cover.test")
    assert STATE_OPEN == state.state

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "CLOSE", 0, False)
    state = opp.states.get("cover.test")
    assert state.state == STATE_CLOSED


async def test_send_open_cover_command(opp, mqtt_mock):
    """Test the sending of open_cover."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 2,
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "OPEN", 2, False)
    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN


async def test_send_close_cover_command(opp, mqtt_mock):
    """Test the sending of close_cover."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 2,
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "CLOSE", 2, False)
    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN


async def test_send_stop_cover_command(opp, mqtt_mock):
    """Test the sending of stop_cover."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 2,
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN

    await opp.services.async_call(
        cover.DOMAIN, SERVICE_STOP_COVER, {ATTR_ENTITY_ID: "cover.test"}, blocking=True
    )

    mqtt_mock.async_publish.assert_called_once_with("command-topic", "STOP", 2, False)
    state = opp.states.get("cover.test")
    assert state.state == STATE_UNKNOWN


async def test_current_cover_position(opp, mqtt_mock):
    """Test the current cover position."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "get-position-topic",
                "command_topic": "command-topic",
                "position_open": 100,
                "position_closed": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    state_attributes_dict = opp.states.get("cover.test").attributes
    assert not ("current_position" in state_attributes_dict)
    assert not ("current_tilt_position" in state_attributes_dict)
    assert not (4 & opp.states.get("cover.test").attributes["supported_features"] == 4)

    async_fire_mqtt_message(opp, "get-position-topic", "0")
    current_cover_position = opp.states.get("cover.test").attributes["current_position"]
    assert current_cover_position == 0

    async_fire_mqtt_message(opp, "get-position-topic", "50")
    current_cover_position = opp.states.get("cover.test").attributes["current_position"]
    assert current_cover_position == 50

    async_fire_mqtt_message(opp, "get-position-topic", "non-numeric")
    current_cover_position = opp.states.get("cover.test").attributes["current_position"]
    assert current_cover_position == 50

    async_fire_mqtt_message(opp, "get-position-topic", "101")
    current_cover_position = opp.states.get("cover.test").attributes["current_position"]
    assert current_cover_position == 100


async def test_current_cover_position_inverted(opp, mqtt_mock):
    """Test the current cover position."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "get-position-topic",
                "command_topic": "command-topic",
                "position_open": 0,
                "position_closed": 100,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    state_attributes_dict = opp.states.get("cover.test").attributes
    assert not ("current_position" in state_attributes_dict)
    assert not ("current_tilt_position" in state_attributes_dict)
    assert not (4 & opp.states.get("cover.test").attributes["supported_features"] == 4)

    async_fire_mqtt_message(opp, "get-position-topic", "100")
    current_percentage_cover_position = opp.states.get("cover.test").attributes[
        "current_position"
    ]
    assert current_percentage_cover_position == 0
    assert opp.states.get("cover.test").state == STATE_CLOSED

    async_fire_mqtt_message(opp, "get-position-topic", "0")
    current_percentage_cover_position = opp.states.get("cover.test").attributes[
        "current_position"
    ]
    assert current_percentage_cover_position == 100
    assert opp.states.get("cover.test").state == STATE_OPEN

    async_fire_mqtt_message(opp, "get-position-topic", "50")
    current_percentage_cover_position = opp.states.get("cover.test").attributes[
        "current_position"
    ]
    assert current_percentage_cover_position == 50
    assert opp.states.get("cover.test").state == STATE_OPEN

    async_fire_mqtt_message(opp, "get-position-topic", "non-numeric")
    current_percentage_cover_position = opp.states.get("cover.test").attributes[
        "current_position"
    ]
    assert current_percentage_cover_position == 50
    assert opp.states.get("cover.test").state == STATE_OPEN

    async_fire_mqtt_message(opp, "get-position-topic", "101")
    current_percentage_cover_position = opp.states.get("cover.test").attributes[
        "current_position"
    ]
    assert current_percentage_cover_position == 0
    assert opp.states.get("cover.test").state == STATE_CLOSED


async def test_set_cover_position(opp, mqtt_mock):
    """Test setting cover position."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "get-position-topic",
                "command_topic": "command-topic",
                "set_position_topic": "set-position-topic",
                "position_open": 100,
                "position_closed": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    state_attributes_dict = opp.states.get("cover.test").attributes
    assert not ("current_position" in state_attributes_dict)
    assert not ("current_tilt_position" in state_attributes_dict)
    assert 4 & opp.states.get("cover.test").attributes["supported_features"] == 4

    async_fire_mqtt_message(opp, "get-position-topic", "22")
    state_attributes_dict = opp.states.get("cover.test").attributes
    assert "current_position" in state_attributes_dict
    assert not ("current_tilt_position" in state_attributes_dict)
    current_cover_position = opp.states.get("cover.test").attributes["current_position"]
    assert current_cover_position == 22


async def test_set_position_templated(opp, mqtt_mock):
    """Test setting cover position via template."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "get-position-topic",
                "command_topic": "command-topic",
                "position_open": 100,
                "position_closed": 0,
                "set_position_topic": "set-position-topic",
                "set_position_template": "{{100-62}}",
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: "cover.test", ATTR_POSITION: 100},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "set-position-topic", "38", 0, False
    )


async def test_set_position_untemplated(opp, mqtt_mock):
    """Test setting cover position via template."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "position_topic": "state-topic",
                "command_topic": "command-topic",
                "set_position_topic": "position-topic",
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: "cover.test", ATTR_POSITION: 62},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("position-topic", 62, 0, False)


async def test_no_command_topic(opp, mqtt_mock):
    """Test with no command topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command",
                "tilt_status_topic": "tilt-status",
            }
        },
    )

    assert opp.states.get("cover.test").attributes["supported_features"] == 240


async def test_no_payload_stop(opp, mqtt_mock):
    """Test with no stop payload."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": None,
            }
        },
    )

    assert opp.states.get("cover.test").attributes["supported_features"] == 3


async def test_with_command_topic_and_tilt(opp, mqtt_mock):
    """Test with command topic and tilt config."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "command_topic": "test",
                "platform": "mqtt",
                "name": "test",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command",
                "tilt_status_topic": "tilt-status",
            }
        },
    )

    assert opp.states.get("cover.test").attributes["supported_features"] == 251


async def test_tilt_defaults(opp, mqtt_mock):
    """Test the defaults."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command",
                "tilt_status_topic": "tilt-status",
            }
        },
    )

    state_attributes_dict = opp.states.get("cover.test").attributes
    assert "current_tilt_position" in state_attributes_dict

    current_cover_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_position == STATE_UNKNOWN


async def test_tilt_via_invocation_defaults(opp, mqtt_mock):
    """Test tilt defaults on close/open."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 100, 0, False)
    mqtt_mock.async_publish.reset_mock()

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 0, 0, False)
    mqtt_mock.async_publish.reset_mock()

    # Close tilt status would be received from device when non-optimistic
    async_fire_mqtt_message(opp, "tilt-status-topic", "0")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 0

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 100, 0, False)
    mqtt_mock.async_publish.reset_mock()

    # Open tilt status would be received from device when non-optimistic
    async_fire_mqtt_message(opp, "tilt-status-topic", "100")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 100

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 0, 0, False)


async def test_tilt_given_value(opp, mqtt_mock):
    """Test tilting to a given value."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_opened_value": 80,
                "tilt_closed_value": 25,
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 80, 0, False)
    mqtt_mock.async_publish.reset_mock()

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 25, 0, False)
    mqtt_mock.async_publish.reset_mock()

    # Close tilt status would be received from device when non-optimistic
    async_fire_mqtt_message(opp, "tilt-status-topic", "25")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 25

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 80, 0, False)
    mqtt_mock.async_publish.reset_mock()

    # Open tilt status would be received from device when non-optimistic
    async_fire_mqtt_message(opp, "tilt-status-topic", "80")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 80

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 25, 0, False)


async def test_tilt_given_value_optimistic(opp, mqtt_mock):
    """Test tilting to a given value."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_opened_value": 80,
                "tilt_closed_value": 25,
                "tilt_optimistic": True,
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 80

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 80, 0, False)
    mqtt_mock.async_publish.reset_mock()

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 25

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 25, 0, False)


async def test_tilt_given_value_altered_range(opp, mqtt_mock):
    """Test tilting to a given value."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_opened_value": 25,
                "tilt_closed_value": 0,
                "tilt_min": 0,
                "tilt_max": 50,
                "tilt_optimistic": True,
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_OPEN_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 50

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 25, 0, False)
    mqtt_mock.async_publish.reset_mock()

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_CLOSE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 0

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 0, 0, False)
    mqtt_mock.async_publish.reset_mock()

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_TOGGLE_COVER_TILT,
        {ATTR_ENTITY_ID: "cover.test"},
        blocking=True,
    )

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 50

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 25, 0, False)


async def test_tilt_via_topic(opp, mqtt_mock):
    """Test tilt by updating status via MQTT."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "tilt-status-topic", "0")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 0

    async_fire_mqtt_message(opp, "tilt-status-topic", "50")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 50


async def test_tilt_via_topic_template(opp, mqtt_mock):
    """Test tilt by updating status via MQTT and template."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_status_template": "{{ (value | multiply(0.01)) | int }}",
                "tilt_opened_value": 400,
                "tilt_closed_value": 125,
            }
        },
    )

    async_fire_mqtt_message(opp, "tilt-status-topic", "99")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 0

    async_fire_mqtt_message(opp, "tilt-status-topic", "5000")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 50


async def test_tilt_via_topic_altered_range(opp, mqtt_mock):
    """Test tilt status via MQTT with altered tilt range."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_min": 0,
                "tilt_max": 50,
            }
        },
    )

    async_fire_mqtt_message(opp, "tilt-status-topic", "0")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 0

    async_fire_mqtt_message(opp, "tilt-status-topic", "50")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 100

    async_fire_mqtt_message(opp, "tilt-status-topic", "25")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 50


async def test_tilt_via_topic_template_altered_range(opp, mqtt_mock):
    """Test tilt status via MQTT and template with altered tilt range."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_status_template": "{{ (value | multiply(0.01)) | int }}",
                "tilt_opened_value": 400,
                "tilt_closed_value": 125,
                "tilt_min": 0,
                "tilt_max": 50,
            }
        },
    )

    async_fire_mqtt_message(opp, "tilt-status-topic", "99")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 0

    async_fire_mqtt_message(opp, "tilt-status-topic", "5000")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 100

    async_fire_mqtt_message(opp, "tilt-status-topic", "2500")

    current_cover_tilt_position = opp.states.get("cover.test").attributes[
        "current_tilt_position"
    ]
    assert current_cover_tilt_position == 50


async def test_tilt_position(opp, mqtt_mock):
    """Test tilt via method invocation."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_TILT_POSITION,
        {ATTR_ENTITY_ID: "cover.test", ATTR_TILT_POSITION: 50},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 50, 0, False)


async def test_tilt_position_altered_range(opp, mqtt_mock):
    """Test tilt via method invocation with altered range."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "qos": 0,
                "payload_open": "OPEN",
                "payload_close": "CLOSE",
                "payload_stop": "STOP",
                "tilt_command_topic": "tilt-command-topic",
                "tilt_status_topic": "tilt-status-topic",
                "tilt_opened_value": 400,
                "tilt_closed_value": 125,
                "tilt_min": 0,
                "tilt_max": 50,
            }
        },
    )

    await opp.services.async_call(
        cover.DOMAIN,
        SERVICE_SET_COVER_TILT_POSITION,
        {ATTR_ENTITY_ID: "cover.test", ATTR_TILT_POSITION: 50},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with("tilt-command-topic", 25, 0, False)


async def test_find_percentage_in_range_defaults(opp, mqtt_mock):
    """Test find percentage in range with default range."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 100,
            "position_closed": 0,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 100,
            "tilt_closed_position": 0,
            "tilt_min": 0,
            "tilt_max": 100,
            "tilt_optimistic": False,
            "tilt_invert_state": False,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_percentage_in_range(44) == 44
    assert mqtt_cover.find_percentage_in_range(44, "cover") == 44


async def test_find_percentage_in_range_altered(opp, mqtt_mock):
    """Test find percentage in range with altered range."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 180,
            "position_closed": 80,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 180,
            "tilt_closed_position": 80,
            "tilt_min": 80,
            "tilt_max": 180,
            "tilt_optimistic": False,
            "tilt_invert_state": False,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_percentage_in_range(120) == 40
    assert mqtt_cover.find_percentage_in_range(120, "cover") == 40


async def test_find_percentage_in_range_defaults_inverted(opp, mqtt_mock):
    """Test find percentage in range with default range but inverted."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 0,
            "position_closed": 100,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 100,
            "tilt_closed_position": 0,
            "tilt_min": 0,
            "tilt_max": 100,
            "tilt_optimistic": False,
            "tilt_invert_state": True,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_percentage_in_range(44) == 56
    assert mqtt_cover.find_percentage_in_range(44, "cover") == 56


async def test_find_percentage_in_range_altered_inverted(opp, mqtt_mock):
    """Test find percentage in range with altered range and inverted."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 80,
            "position_closed": 180,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 180,
            "tilt_closed_position": 80,
            "tilt_min": 80,
            "tilt_max": 180,
            "tilt_optimistic": False,
            "tilt_invert_state": True,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_percentage_in_range(120) == 60
    assert mqtt_cover.find_percentage_in_range(120, "cover") == 60


async def test_find_in_range_defaults(opp, mqtt_mock):
    """Test find in range with default range."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 100,
            "position_closed": 0,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 100,
            "tilt_closed_position": 0,
            "tilt_min": 0,
            "tilt_max": 100,
            "tilt_optimistic": False,
            "tilt_invert_state": False,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_in_range_from_percent(44) == 44
    assert mqtt_cover.find_in_range_from_percent(44, "cover") == 44


async def test_find_in_range_altered(opp, mqtt_mock):
    """Test find in range with altered range."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 180,
            "position_closed": 80,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 180,
            "tilt_closed_position": 80,
            "tilt_min": 80,
            "tilt_max": 180,
            "tilt_optimistic": False,
            "tilt_invert_state": False,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_in_range_from_percent(40) == 120
    assert mqtt_cover.find_in_range_from_percent(40, "cover") == 120


async def test_find_in_range_defaults_inverted(opp, mqtt_mock):
    """Test find in range with default range but inverted."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 0,
            "position_closed": 100,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 100,
            "tilt_closed_position": 0,
            "tilt_min": 0,
            "tilt_max": 100,
            "tilt_optimistic": False,
            "tilt_invert_state": True,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_in_range_from_percent(56) == 44
    assert mqtt_cover.find_in_range_from_percent(56, "cover") == 44


async def test_find_in_range_altered_inverted(opp, mqtt_mock):
    """Test find in range with altered range and inverted."""
    mqtt_cover = MqttCover(
        {
            "name": "cover.test",
            "state_topic": "state-topic",
            "get_position_topic": None,
            "command_topic": "command-topic",
            "availability_topic": None,
            "tilt_command_topic": "tilt-command-topic",
            "tilt_status_topic": "tilt-status-topic",
            "qos": 0,
            "retain": False,
            "state_open": "OPEN",
            "state_closed": "CLOSE",
            "position_open": 80,
            "position_closed": 180,
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_stop": "STOP",
            "payload_available": None,
            "payload_not_available": None,
            "optimistic": False,
            "value_template": None,
            "tilt_open_position": 180,
            "tilt_closed_position": 80,
            "tilt_min": 80,
            "tilt_max": 180,
            "tilt_optimistic": False,
            "tilt_invert_state": True,
            "set_position_topic": None,
            "set_position_template": None,
            "unique_id": None,
            "device_config": None,
        },
        None,
        None,
    )

    assert mqtt_cover.find_in_range_from_percent(60) == 120
    assert mqtt_cover.find_in_range_from_percent(60, "cover") == 120


async def test_availability_without_topic(opp, mqtt_mock):
    """Test availability without defined availability topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state != STATE_UNAVAILABLE


async def test_availability_by_defaults(opp, mqtt_mock):
    """Test availability by defaults with defined topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "availability_topic": "availability-topic",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "online")
    await opp.async_block_till_done()

    state = opp.states.get("cover.test")
    assert state.state != STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "offline")
    await opp.async_block_till_done()

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNAVAILABLE


async def test_availability_by_custom_payload(opp, mqtt_mock):
    """Test availability by custom payload with defined topic."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "state-topic",
                "command_topic": "command-topic",
                "availability_topic": "availability-topic",
                "payload_available": "good",
                "payload_not_available": "nogood",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "good")
    await opp.async_block_till_done()

    state = opp.states.get("cover.test")
    assert state.state != STATE_UNAVAILABLE

    async_fire_mqtt_message(opp, "availability-topic", "nogood")
    await opp.async_block_till_done()

    state = opp.states.get("cover.test")
    assert state.state == STATE_UNAVAILABLE


async def test_valid_device_class(opp, mqtt_mock):
    """Test the setting of a valid sensor class."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "device_class": "garage",
                "state_topic": "test-topic",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state.attributes.get("device_class") == "garage"


async def test_invalid_device_class(opp, mqtt_mock):
    """Test the setting of an invalid sensor class."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "device_class": "abc123",
                "state_topic": "test-topic",
            }
        },
    )

    state = opp.states.get("cover.test")
    assert state is None


async def test_setting_attribute_via_mqtt_json_message(opp, mqtt_mock):
    """Test the setting of attribute via MQTT with JSON payload."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '{ "val": "100" }')
    state = opp.states.get("cover.test")

    assert state.attributes.get("val") == "100"


async def test_update_with_json_attrs_not_dict(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", '[ "list", "of", "things"]')
    state = opp.states.get("cover.test")

    assert state.attributes.get("val") is None
    assert "JSON result was not a dictionary" in caplog.text


async def test_update_with_json_attrs_bad_JSON(opp, mqtt_mock, caplog):
    """Test attributes get extracted from a JSON result."""
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: {
                "platform": "mqtt",
                "name": "test",
                "state_topic": "test-topic",
                "json_attributes_topic": "attr-topic",
            }
        },
    )

    async_fire_mqtt_message(opp, "attr-topic", "This is not JSON")

    state = opp.states.get("cover.test")
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
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data1)
    await opp.async_block_till_done()
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "100" }')
    state = opp.states.get("cover.beer")
    assert state.attributes.get("val") == "100"

    # Change json_attributes_topic
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data2)
    await opp.async_block_till_done()

    # Verify we are no longer subscribing to the old topic
    async_fire_mqtt_message(opp, "attr-topic1", '{ "val": "50" }')
    state = opp.states.get("cover.beer")
    assert state.attributes.get("val") == "100"

    # Verify we are subscribing to the new topic
    async_fire_mqtt_message(opp, "attr-topic2", '{ "val": "75" }')
    state = opp.states.get("cover.beer")
    assert state.attributes.get("val") == "75"


async def test_discovery_removal_cover(opp, mqtt_mock, caplog):
    """Test removal of discovered cover."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data = '{ "name": "Beer",' '  "command_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data)
    await opp.async_block_till_done()
    state = opp.states.get("cover.beer")
    assert state is not None
    assert state.name == "Beer"
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", "")
    await opp.async_block_till_done()
    state = opp.states.get("cover.beer")
    assert state is None


async def test_discovery_update_cover(opp, mqtt_mock, caplog):
    """Test update of discovered cover."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)
    data1 = '{ "name": "Beer",' '  "command_topic": "test_topic" }'
    data2 = '{ "name": "Milk",' '  "command_topic": "test_topic" }'
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data1)
    await opp.async_block_till_done()
    state = opp.states.get("cover.beer")
    assert state is not None
    assert state.name == "Beer"

    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("cover.beer")
    assert state is not None
    assert state.name == "Milk"

    state = opp.states.get("cover.milk")
    assert state is None


async def test_discovery_broken(opp, mqtt_mock, caplog):
    """Test handling of bad discovery message."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)
    await async_start(opp, "openpeerpower", {}, entry)

    data1 = '{ "name": "Beer",' '  "command_topic": "test_topic#" }'
    data2 = '{ "name": "Milk",' '  "command_topic": "test_topic" }'

    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data1)
    await opp.async_block_till_done()

    state = opp.states.get("cover.beer")
    assert state is None

    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data2)
    await opp.async_block_till_done()

    state = opp.states.get("cover.milk")
    assert state is not None
    assert state.name == "Milk"
    state = opp.states.get("cover.beer")
    assert state is None


async def test_unique_id(opp):
    """Test unique_id option only creates one cover per id."""
    await async_mock_mqtt_component(opp)
    assert await async_setup_component(
        opp,
        cover.DOMAIN,
        {
            cover.DOMAIN: [
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

    assert len(opp.states.async_entity_ids(cover.DOMAIN)) == 1


async def test_entity_device_info_with_identifier(opp, mqtt_mock):
    """Test MQTT cover device registry integration."""
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
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data)
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
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data)
    await opp.async_block_till_done()

    device = registry.async_get_device({("mqtt", "helloworld")}, set())
    assert device is not None
    assert device.name == "Beer"

    config["device"]["name"] = "Milk"
    data = json.dumps(config)
    async_fire_mqtt_message(opp, "openpeerpower/cover/bla/config", data)
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
        cover.DOMAIN,
        {
            cover.DOMAIN: [
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

    state = opp.states.get("cover.beer")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.reset_mock()

    registry.async_update_entity("cover.beer", new_entity_id="cover.milk")
    await opp.async_block_till_done()

    state = opp.states.get("cover.beer")
    assert state is None

    state = opp.states.get("cover.milk")
    assert state is not None
    assert mock_mqtt.async_subscribe.call_count == 2
    mock_mqtt.async_subscribe.assert_any_call("test-topic", ANY, 0, "utf-8")
    mock_mqtt.async_subscribe.assert_any_call("avty-topic", ANY, 0, "utf-8")
