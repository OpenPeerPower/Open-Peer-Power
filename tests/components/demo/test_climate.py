"""The tests for the demo climate component."""

import pytest
import voluptuous as vol

from openpeerpower.components.climate.const import (
    ATTR_AUX_HEAT,
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODES,
    ATTR_MAX_HUMIDITY,
    ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_ECO,
)
from openpeerpower.const import ATTR_TEMPERATURE, STATE_OFF, STATE_ON
from openpeerpower.setup import async_setup_component
from openpeerpower.util.unit_system import METRIC_SYSTEM

from tests.components.climate import common

ENTITY_CLIMATE = "climate.hvac"
ENTITY_ECOBEE = "climate.ecobee"
ENTITY_HEATPUMP = "climate.heatpump"


@pytest.fixture(autouse=True)
async def setup_demo_climate(opp):
    """Initialize setup demo climate."""
    opp.config.units = METRIC_SYSTEM
    assert await async_setup_component(opp, DOMAIN, {"climate": {"platform": "demo"}})


def test_setup_params(opp):
    """Test the initial parameters."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_COOL
    assert 21 == state.attributes.get(ATTR_TEMPERATURE)
    assert 22 == state.attributes.get(ATTR_CURRENT_TEMPERATURE)
    assert "On High" == state.attributes.get(ATTR_FAN_MODE)
    assert 67 == state.attributes.get(ATTR_HUMIDITY)
    assert 54 == state.attributes.get(ATTR_CURRENT_HUMIDITY)
    assert "Off" == state.attributes.get(ATTR_SWING_MODE)
    assert STATE_OFF == state.attributes.get(ATTR_AUX_HEAT)
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        "off",
        "heat",
        "cool",
        "auto",
        "dry",
        "fan_only",
    ]


def test_default_setup_params(opp):
    """Test the setup with default parameters."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert 7 == state.attributes.get(ATTR_MIN_TEMP)
    assert 35 == state.attributes.get(ATTR_MAX_TEMP)
    assert 30 == state.attributes.get(ATTR_MIN_HUMIDITY)
    assert 99 == state.attributes.get(ATTR_MAX_HUMIDITY)


async def test_set_only_target_temp_bad_attr(opp):
    """Test setting the target temperature without required attribute."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert 21 == state.attributes.get(ATTR_TEMPERATURE)

    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(opp, None, ENTITY_CLIMATE)

    await opp.async_block_till_done()
    assert 21 == state.attributes.get(ATTR_TEMPERATURE)


async def test_set_only_target_temp(opp):
    """Test the setting of the target temperature."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert 21 == state.attributes.get(ATTR_TEMPERATURE)

    await common.async_set_temperature(opp, 30, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert 30.0 == state.attributes.get(ATTR_TEMPERATURE)


async def test_set_only_target_temp_with_convert(opp):
    """Test the setting of the target temperature."""
    state = opp.states.get(ENTITY_HEATPUMP)
    assert 20 == state.attributes.get(ATTR_TEMPERATURE)

    await common.async_set_temperature(opp, 21, ENTITY_HEATPUMP)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_HEATPUMP)
    assert 21.0 == state.attributes.get(ATTR_TEMPERATURE)


async def test_set_target_temp_range(opp):
    """Test the setting of the target temperature with range."""
    state = opp.states.get(ENTITY_ECOBEE)
    assert state.attributes.get(ATTR_TEMPERATURE) is None
    assert 21.0 == state.attributes.get(ATTR_TARGET_TEMP_LOW)
    assert 24.0 == state.attributes.get(ATTR_TARGET_TEMP_HIGH)

    await common.async_set_temperature(
        opp, target_temp_high=25, target_temp_low=20, entity_id=ENTITY_ECOBEE
    )
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_ECOBEE)
    assert state.attributes.get(ATTR_TEMPERATURE) is None
    assert 20.0 == state.attributes.get(ATTR_TARGET_TEMP_LOW)
    assert 25.0 == state.attributes.get(ATTR_TARGET_TEMP_HIGH)


async def test_set_target_temp_range_bad_attr(opp):
    """Test setting the target temperature range without attribute."""
    state = opp.states.get(ENTITY_ECOBEE)
    assert state.attributes.get(ATTR_TEMPERATURE) is None
    assert 21.0 == state.attributes.get(ATTR_TARGET_TEMP_LOW)
    assert 24.0 == state.attributes.get(ATTR_TARGET_TEMP_HIGH)

    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(
            opp,
            temperature=None,
            entity_id=ENTITY_ECOBEE,
            target_temp_low=None,
            target_temp_high=None,
        )
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_ECOBEE)
    assert state.attributes.get(ATTR_TEMPERATURE) is None
    assert 21.0 == state.attributes.get(ATTR_TARGET_TEMP_LOW)
    assert 24.0 == state.attributes.get(ATTR_TARGET_TEMP_HIGH)


async def test_set_target_humidity_bad_attr(opp):
    """Test setting the target humidity without required attribute."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert 67 == state.attributes.get(ATTR_HUMIDITY)

    with pytest.raises(vol.Invalid):
        await common.async_set_humidity(opp, None, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert 67 == state.attributes.get(ATTR_HUMIDITY)


async def test_set_target_humidity(opp):
    """Test the setting of the target humidity."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert 67 == state.attributes.get(ATTR_HUMIDITY)

    await common.async_set_humidity(opp, 64, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert 64.0 == state.attributes.get(ATTR_HUMIDITY)


async def test_set_fan_mode_bad_attr(opp):
    """Test setting fan mode without required attribute."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert "On High" == state.attributes.get(ATTR_FAN_MODE)

    with pytest.raises(vol.Invalid):
        await common.async_set_fan_mode(opp, None, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert "On High" == state.attributes.get(ATTR_FAN_MODE)


async def test_set_fan_mode(opp):
    """Test setting of new fan mode."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert "On High" == state.attributes.get(ATTR_FAN_MODE)

    await common.async_set_fan_mode(opp, "On Low", ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert "On Low" == state.attributes.get(ATTR_FAN_MODE)


async def test_set_swing_mode_bad_attr(opp):
    """Test setting swing mode without required attribute."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert "Off" == state.attributes.get(ATTR_SWING_MODE)

    with pytest.raises(vol.Invalid):
        await common.async_set_swing_mode(opp, None, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert "Off" == state.attributes.get(ATTR_SWING_MODE)


async def test_set_swing(opp):
    """Test setting of new swing mode."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert "Off" == state.attributes.get(ATTR_SWING_MODE)

    await common.async_set_swing_mode(opp, "Auto", ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert "Auto" == state.attributes.get(ATTR_SWING_MODE)


async def test_set_hvac_bad_attr_and_state(opp):
    """Test setting hvac mode without required attribute.

    Also check the state.
    """
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.attributes.get(ATTR_HVAC_ACTION) == CURRENT_HVAC_COOL
    assert state.state == HVAC_MODE_COOL

    with pytest.raises(vol.Invalid):
        await common.async_set_hvac_mode(opp, None, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert state.attributes.get(ATTR_HVAC_ACTION) == CURRENT_HVAC_COOL
    assert state.state == HVAC_MODE_COOL


async def test_set_hvac(opp):
    """Test setting of new hvac mode."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_COOL

    await common.async_set_hvac_mode(opp, HVAC_MODE_HEAT, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_HEAT


async def test_set_hold_mode_away(opp):
    """Test setting the hold mode away."""
    await common.async_set_preset_mode(opp, PRESET_AWAY, ENTITY_ECOBEE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_ECOBEE)
    assert state.attributes.get(ATTR_PRESET_MODE) == PRESET_AWAY


async def test_set_hold_mode_eco(opp):
    """Test setting the hold mode eco."""
    await common.async_set_preset_mode(opp, PRESET_ECO, ENTITY_ECOBEE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_ECOBEE)
    assert state.attributes.get(ATTR_PRESET_MODE) == PRESET_ECO


async def test_set_aux_heat_bad_attr(opp):
    """Test setting the auxiliary heater without required attribute."""
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.attributes.get(ATTR_AUX_HEAT) == STATE_OFF

    with pytest.raises(vol.Invalid):
        await common.async_set_aux_heat(opp, None, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    assert state.attributes.get(ATTR_AUX_HEAT) == STATE_OFF


async def test_set_aux_heat_on(opp):
    """Test setting the axillary heater on/true."""
    await common.async_set_aux_heat(opp, True, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert state.attributes.get(ATTR_AUX_HEAT) == STATE_ON


async def test_set_aux_heat_off(opp):
    """Test setting the auxiliary heater off/false."""
    await common.async_set_aux_heat(opp, False, ENTITY_CLIMATE)
    await opp.async_block_till_done()

    state = opp.states.get(ENTITY_CLIMATE)
    assert state.attributes.get(ATTR_AUX_HEAT) == STATE_OFF


async def test_turn_on(opp):
    """Test turn on device."""
    await common.async_set_hvac_mode(opp, HVAC_MODE_OFF, ENTITY_CLIMATE)
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_OFF

    await common.async_turn_on(opp, ENTITY_CLIMATE)
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_HEAT


async def test_turn_off(opp):
    """Test turn on device."""
    await common.async_set_hvac_mode(opp, HVAC_MODE_HEAT, ENTITY_CLIMATE)
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_HEAT

    await common.async_turn_off(opp, ENTITY_CLIMATE)
    state = opp.states.get(ENTITY_CLIMATE)
    assert state.state == HVAC_MODE_OFF
