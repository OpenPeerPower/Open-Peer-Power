"""The tests for the MQTT discovery."""
from pathlib import Path
import re
from unittest.mock import patch

from openpeerpower.components import mqtt
from openpeerpower.components.mqtt.abbreviations import (
    ABBREVIATIONS,
    DEVICE_ABBREVIATIONS,
)
from openpeerpower.components.mqtt.discovery import ALREADY_DISCOVERED, async_start
from openpeerpower.const import STATE_OFF, STATE_ON

from tests.common import MockConfigEntry, async_fire_mqtt_message, mock_coro


async def test_subscribing_config_topic(opp, mqtt_mock):
    """Test setting up discovery."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN, data={mqtt.CONF_BROKER: "test-broker"})

    opp_config = {}
    discovery_topic = "openpeerpower"
    await async_start(opp, discovery_topic, opp_config, entry)

    assert mqtt_mock.async_subscribe.called
    call_args = mqtt_mock.async_subscribe.mock_calls[0][1]
    assert call_args[0] == discovery_topic + "/#"
    assert call_args[2] == 0


async def test_invalid_topic(opp, mqtt_mock):
    """Test sending to invalid topic."""
    with patch(
        "openpeerpower.components.mqtt.discovery.async_load_platform"
    ) as mock_load_platform:
        entry = MockConfigEntry(
            domain=mqtt.DOMAIN, data={mqtt.CONF_BROKER: "test-broker"}
        )

        mock_load_platform.return_value = mock_coro()
        await async_start(opp, "openpeerpower", {}, entry)

        async_fire_mqtt_message(
            opp, "openpeerpower/binary_sensor/bla/not_config", "{}"
        )
        await opp.async_block_till_done()
        assert not mock_load_platform.called


async def test_invalid_json(opp, mqtt_mock, caplog):
    """Test sending in invalid JSON."""
    with patch(
        "openpeerpower.components.mqtt.discovery.async_load_platform"
    ) as mock_load_platform:
        entry = MockConfigEntry(
            domain=mqtt.DOMAIN, data={mqtt.CONF_BROKER: "test-broker"}
        )

        mock_load_platform.return_value = mock_coro()
        await async_start(opp, "openpeerpower", {}, entry)

        async_fire_mqtt_message(
            opp, "openpeerpower/binary_sensor/bla/config", "not json"
        )
        await opp.async_block_till_done()
        assert "Unable to parse JSON" in caplog.text
        assert not mock_load_platform.called


async def test_only_valid_components(opp, mqtt_mock, caplog):
    """Test for a valid component."""
    with patch(
        "openpeerpower.components.mqtt.discovery.async_load_platform"
    ) as mock_load_platform:
        entry = MockConfigEntry(domain=mqtt.DOMAIN)

        invalid_component = "timer"

        mock_load_platform.return_value = mock_coro()
        await async_start(opp, "openpeerpower", {}, entry)

        async_fire_mqtt_message(
            opp, "openpeerpower/{}/bla/config".format(invalid_component), "{}"
        )

    await opp.async_block_till_done()

    assert "Integration {} is not supported".format(invalid_component) in caplog.text

    assert not mock_load_platform.called


async def test_correct_config_discovery(opp, mqtt_mock, caplog):
    """Test sending in correct JSON."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    async_fire_mqtt_message(
        opp, "openpeerpower/binary_sensor/bla/config", '{ "name": "Beer" }'
    )
    await opp.async_block_till_done()

    state = opp.states.get("binary_sensor.beer")

    assert state is not None
    assert state.name == "Beer"
    assert ("binary_sensor", "bla") in opp.data[ALREADY_DISCOVERED]


async def test_discover_fan(opp, mqtt_mock, caplog):
    """Test discovering an MQTT fan."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    async_fire_mqtt_message(
        opp,
        "openpeerpower/fan/bla/config",
        ('{ "name": "Beer",' '  "command_topic": "test_topic" }'),
    )
    await opp.async_block_till_done()

    state = opp.states.get("fan.beer")

    assert state is not None
    assert state.name == "Beer"
    assert ("fan", "bla") in opp.data[ALREADY_DISCOVERED]


async def test_discover_climate(opp, mqtt_mock, caplog):
    """Test discovering an MQTT climate component."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = (
        '{ "name": "ClimateTest",'
        '  "current_temperature_topic": "climate/bla/current_temp",'
        '  "temperature_command_topic": "climate/bla/target_temp" }'
    )

    async_fire_mqtt_message(opp, "openpeerpower/climate/bla/config", data)
    await opp.async_block_till_done()

    state = opp.states.get("climate.ClimateTest")

    assert state is not None
    assert state.name == "ClimateTest"
    assert ("climate", "bla") in opp.data[ALREADY_DISCOVERED]


async def test_discover_alarm_control_panel(opp, mqtt_mock, caplog):
    """Test discovering an MQTT alarm control panel component."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = (
        '{ "name": "AlarmControlPanelTest",'
        '  "state_topic": "test_topic",'
        '  "command_topic": "test_topic" }'
    )

    async_fire_mqtt_message(opp, "openpeerpower/alarm_control_panel/bla/config", data)
    await opp.async_block_till_done()

    state = opp.states.get("alarm_control_panel.AlarmControlPanelTest")

    assert state is not None
    assert state.name == "AlarmControlPanelTest"
    assert ("alarm_control_panel", "bla") in opp.data[ALREADY_DISCOVERED]


async def test_discovery_incl_nodeid(opp, mqtt_mock, caplog):
    """Test sending in correct JSON with optional node_id included."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    async_fire_mqtt_message(
        opp, "openpeerpower/binary_sensor/my_node_id/bla/config", '{ "name": "Beer" }',
    )
    await opp.async_block_till_done()

    state = opp.states.get("binary_sensor.beer")

    assert state is not None
    assert state.name == "Beer"
    assert ("binary_sensor", "my_node_id bla") in opp.data[ALREADY_DISCOVERED]


async def test_non_duplicate_discovery(opp, mqtt_mock, caplog):
    """Test for a non duplicate component."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    async_fire_mqtt_message(
        opp, "openpeerpower/binary_sensor/bla/config", '{ "name": "Beer" }'
    )
    async_fire_mqtt_message(
        opp, "openpeerpower/binary_sensor/bla/config", '{ "name": "Beer" }'
    )
    await opp.async_block_till_done()

    state = opp.states.get("binary_sensor.beer")
    state_duplicate = opp.states.get("binary_sensor.beer1")

    assert state is not None
    assert state.name == "Beer"
    assert state_duplicate is None
    assert "Component has already been discovered: binary_sensor bla" in caplog.text


async def test_discovery_expansion(opp, mqtt_mock, caplog):
    """Test expansion of abbreviated discovery payload."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = (
        '{ "~": "some/base/topic",'
        '  "name": "DiscoveryExpansionTest1",'
        '  "stat_t": "test_topic/~",'
        '  "cmd_t": "~/test_topic",'
        '  "dev":{'
        '    "ids":["5706DF"],'
        '    "name":"DiscoveryExpansionTest1 Device",'
        '    "mdl":"Generic",'
        '    "sw":"1.2.3.4",'
        '    "mf":"None"'
        "  }"
        "}"
    )

    async_fire_mqtt_message(opp, "openpeerpower/switch/bla/config", data)
    await opp.async_block_till_done()

    state = opp.states.get("switch.DiscoveryExpansionTest1")
    assert state is not None
    assert state.name == "DiscoveryExpansionTest1"
    assert ("switch", "bla") in opp.data[ALREADY_DISCOVERED]
    assert state.state == STATE_OFF

    async_fire_mqtt_message(opp, "test_topic/some/base/topic", "ON")

    state = opp.states.get("switch.DiscoveryExpansionTest1")
    assert state.state == STATE_ON


ABBREVIATIONS_WHITE_LIST = [
    # MQTT client/server/trigger settings
    "CONF_BIRTH_MESSAGE",
    "CONF_BROKER",
    "CONF_CERTIFICATE",
    "CONF_CLIENT_CERT",
    "CONF_CLIENT_ID",
    "CONF_CLIENT_KEY",
    "CONF_DISCOVERY",
    "CONF_DISCOVERY_ID",
    "CONF_DISCOVERY_PREFIX",
    "CONF_EMBEDDED",
    "CONF_KEEPALIVE",
    "CONF_TLS_INSECURE",
    "CONF_TLS_VERSION",
    "CONF_WILL_MESSAGE",
    # Undocumented device configuration
    "CONF_DEPRECATED_VIA_HUB",
    "CONF_VIA_DEVICE",
    # Already short
    "CONF_FAN_MODE_LIST",
    "CONF_HOLD_LIST",
    "CONF_HS",
    "CONF_MODE_LIST",
    "CONF_PRECISION",
    "CONF_QOS",
    "CONF_SCHEMA",
    "CONF_SWING_MODE_LIST",
    "CONF_TEMP_STEP",
]


async def test_missing_discover_abbreviations(opp, mqtt_mock, caplog):
    """Check MQTT platforms for missing abbreviations."""
    missing = []
    regex = re.compile(r"(CONF_[a-zA-Z\d_]*) *= *[\'\"]([a-zA-Z\d_]*)[\'\"]")
    for fil in Path(mqtt.__file__).parent.rglob("*.py"):
        with open(fil) as file:
            matches = re.findall(regex, file.read())
            for match in matches:
                if (
                    match[1] not in ABBREVIATIONS.values()
                    and match[1] not in DEVICE_ABBREVIATIONS.values()
                    and match[0] not in ABBREVIATIONS_WHITE_LIST
                ):
                    missing.append(
                        "{}: no abbreviation for {} ({})".format(
                            fil, match[1], match[0]
                        )
                    )

    assert not missing


async def test_implicit_state_topic_alarm(opp, mqtt_mock, caplog):
    """Test implicit state topic for alarm_control_panel."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = (
        '{ "name": "Test1",'
        '  "command_topic": "openpeerpower/alarm_control_panel/bla/cmnd"'
        "}"
    )

    async_fire_mqtt_message(opp, "openpeerpower/alarm_control_panel/bla/config", data)
    await opp.async_block_till_done()
    assert (
        "implicit state_topic is deprecated, add "
        '"state_topic":"openpeerpower/alarm_control_panel/bla/state"' in caplog.text
    )

    state = opp.states.get("alarm_control_panel.Test1")
    assert state is not None
    assert state.name == "Test1"
    assert ("alarm_control_panel", "bla") in opp.data[ALREADY_DISCOVERED]
    assert state.state == "unknown"

    async_fire_mqtt_message(
        opp, "openpeerpower/alarm_control_panel/bla/state", "armed_away"
    )

    state = opp.states.get("alarm_control_panel.Test1")
    assert state.state == "armed_away"


async def test_implicit_state_topic_binary_sensor(opp, mqtt_mock, caplog):
    """Test implicit state topic for binary_sensor."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = '{ "name": "Test1"' "}"

    async_fire_mqtt_message(opp, "openpeerpower/binary_sensor/bla/config", data)
    await opp.async_block_till_done()
    assert (
        "implicit state_topic is deprecated, add "
        '"state_topic":"openpeerpower/binary_sensor/bla/state"' in caplog.text
    )

    state = opp.states.get("binary_sensor.Test1")
    assert state is not None
    assert state.name == "Test1"
    assert ("binary_sensor", "bla") in opp.data[ALREADY_DISCOVERED]
    assert state.state == "off"

    async_fire_mqtt_message(opp, "openpeerpower/binary_sensor/bla/state", "ON")

    state = opp.states.get("binary_sensor.Test1")
    assert state.state == "on"


async def test_implicit_state_topic_sensor(opp, mqtt_mock, caplog):
    """Test implicit state topic for sensor."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = '{ "name": "Test1"' "}"

    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/config", data)
    await opp.async_block_till_done()
    assert (
        "implicit state_topic is deprecated, add "
        '"state_topic":"openpeerpower/sensor/bla/state"' in caplog.text
    )

    state = opp.states.get("sensor.Test1")
    assert state is not None
    assert state.name == "Test1"
    assert ("sensor", "bla") in opp.data[ALREADY_DISCOVERED]
    assert state.state == "unknown"

    async_fire_mqtt_message(opp, "openpeerpower/sensor/bla/state", "1234")

    state = opp.states.get("sensor.Test1")
    assert state.state == "1234"


async def test_no_implicit_state_topic_switch(opp, mqtt_mock, caplog):
    """Test no implicit state topic for switch."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "openpeerpower", {}, entry)

    data = '{ "name": "Test1",' '  "command_topic": "cmnd"' "}"

    async_fire_mqtt_message(opp, "openpeerpower/switch/bla/config", data)
    await opp.async_block_till_done()
    assert "implicit state_topic is deprecated" not in caplog.text

    state = opp.states.get("switch.Test1")
    assert state is not None
    assert state.name == "Test1"
    assert ("switch", "bla") in opp.data[ALREADY_DISCOVERED]
    assert state.state == "off"
    assert state.attributes["assumed_state"] is True

    async_fire_mqtt_message(opp, "openpeerpower/switch/bla/state", "ON")

    state = opp.states.get("switch.Test1")
    assert state.state == "off"


async def test_complex_discovery_topic_prefix(opp, mqtt_mock, caplog):
    """Tests handling of discovery topic prefix with multiple slashes."""
    entry = MockConfigEntry(domain=mqtt.DOMAIN)

    await async_start(opp, "my_home/openpeerpower/register", {}, entry)

    async_fire_mqtt_message(
        opp,
        ("my_home/openpeerpower/register/binary_sensor/node1/object1/config"),
        '{ "name": "Beer" }',
    )
    await opp.async_block_till_done()

    state = opp.states.get("binary_sensor.beer")

    assert state is not None
    assert state.name == "Beer"
    assert ("binary_sensor", "node1 object1") in opp.data[ALREADY_DISCOVERED]
