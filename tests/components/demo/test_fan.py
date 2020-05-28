"""Test cases around the demo fan platform."""
import pytest

from openpeerpower.components import fan
from openpeerpower.const import STATE_OFF, STATE_ON
from openpeerpower.setup import async_setup_component

from tests.components.fan import common

FAN_ENTITY_ID = "fan.living_room_fan"


def get_entity(opp):
    """Get the fan entity."""
    return opp.states.get(FAN_ENTITY_ID)


@pytest.fixture(autouse=True)
def setup_comp(opp):
    """Initialize components."""
    opp.loop.run_until_complete(
        async_setup_component(opp, fan.DOMAIN, {"fan": {"platform": "demo"}})
    )


async def test_turn_on(opp):
    """Test turning on the device."""
    assert STATE_OFF == get_entity(opp).state

    await common.async_turn_on(opp, FAN_ENTITY_ID)
    assert STATE_OFF != get_entity(opp).state

    await common.async_turn_on(opp, FAN_ENTITY_ID, fan.SPEED_HIGH)
    assert STATE_ON == get_entity(opp).state
    assert fan.SPEED_HIGH == get_entity(opp).attributes[fan.ATTR_SPEED]


async def test_turn_off(opp):
    """Test turning off the device."""
    assert STATE_OFF == get_entity(opp).state

    await common.async_turn_on(opp, FAN_ENTITY_ID)
    assert STATE_OFF != get_entity(opp).state

    await common.async_turn_off(opp, FAN_ENTITY_ID)
    assert STATE_OFF == get_entity(opp).state


async def test_turn_off_without_entity_id(opp):
    """Test turning off all fans."""
    assert STATE_OFF == get_entity(opp).state

    await common.async_turn_on(opp, FAN_ENTITY_ID)
    assert STATE_OFF != get_entity(opp).state

    await common.async_turn_off(opp)
    assert STATE_OFF == get_entity(opp).state


async def test_set_direction(opp):
    """Test setting the direction of the device."""
    assert STATE_OFF == get_entity(opp).state

    await common.async_set_direction(opp, FAN_ENTITY_ID, fan.DIRECTION_REVERSE)
    assert fan.DIRECTION_REVERSE == get_entity(opp).attributes.get("direction")


async def test_set_speed(opp):
    """Test setting the speed of the device."""
    assert STATE_OFF == get_entity(opp).state

    await common.async_set_speed(opp, FAN_ENTITY_ID, fan.SPEED_LOW)
    assert fan.SPEED_LOW == get_entity(opp).attributes.get("speed")


async def test_oscillate(opp):
    """Test oscillating the fan."""
    assert not get_entity(opp).attributes.get("oscillating")

    await common.async_oscillate(opp, FAN_ENTITY_ID, True)
    assert get_entity(opp).attributes.get("oscillating")

    await common.async_oscillate(opp, FAN_ENTITY_ID, False)
    assert not get_entity(opp).attributes.get("oscillating")


async def test_is_on(opp):
    """Test is on service call."""
    assert not fan.is_on(opp, FAN_ENTITY_ID)

    await common.async_turn_on(opp, FAN_ENTITY_ID)
    assert fan.is_on(opp, FAN_ENTITY_ID)
