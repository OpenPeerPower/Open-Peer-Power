"""The tests for the Demo cover platform."""
from datetime import timedelta

import pytest

from openpeerpower.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN,
)
from openpeerpower.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_CLOSE_COVER,
    SERVICE_CLOSE_COVER_TILT,
    SERVICE_OPEN_COVER,
    SERVICE_OPEN_COVER_TILT,
    SERVICE_SET_COVER_POSITION,
    SERVICE_SET_COVER_TILT_POSITION,
    SERVICE_STOP_COVER,
    SERVICE_STOP_COVER_TILT,
    SERVICE_TOGGLE,
    SERVICE_TOGGLE_COVER_TILT,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import assert_setup_component, async_fire_time_changed

CONFIG = {"cover": {"platform": "demo"}}
ENTITY_COVER = "cover.living_room_window"


@pytest.fixture
async def setup_comp(opp):
    """Set up demo cover component."""
    with assert_setup_component(1, DOMAIN):
        await async_setup_component(opp, DOMAIN, CONFIG)


async def test_supported_features(opp, setup_comp):
    """Test cover supported features."""
    state = opp.states.get("cover.garage_door")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 3
    state = opp.states.get("cover.kitchen_window")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 11
    state = opp.states.get("cover.hall_window")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 15
    state = opp.states.get("cover.living_room_window")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == 255


async def test_close_cover(opp, setup_comp):
    """Test closing the cover."""
    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 70

    await opp.services.async_call(
        DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_CLOSING
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_CLOSED
    assert state.attributes[ATTR_CURRENT_POSITION] == 0


async def test_open_cover(opp, setup_comp):
    """Test opening the cover."""
    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 70
    await opp.services.async_call(
        DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_OPENING
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 100


async def test_toggle_cover(opp, setup_comp):
    """Test toggling the cover."""
    # Start open
    await opp.services.async_call(
        DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_OPEN
    assert state.attributes["current_position"] == 100
    # Toggle closed
    await opp.services.async_call(
        DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_CLOSED
    assert state.attributes[ATTR_CURRENT_POSITION] == 0
    # Toggle open
    await opp.services.async_call(
        DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.state == STATE_OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 100


async def test_set_cover_position(opp, setup_comp):
    """Test moving the cover to a specific position."""
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_POSITION] == 70
    await opp.services.async_call(
        DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: ENTITY_COVER, ATTR_POSITION: 10},
        blocking=True,
    )
    for _ in range(6):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_POSITION] == 10


async def test_stop_cover(opp, setup_comp):
    """Test stopping the cover."""
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_POSITION] == 70
    await opp.services.async_call(
        DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    future = dt_util.utcnow() + timedelta(seconds=1)
    async_fire_time_changed(opp, future)
    await opp.async_block_till_done()
    await opp.services.async_call(
        DOMAIN, SERVICE_STOP_COVER, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    async_fire_time_changed(opp, future)
    await opp.async_block_till_done()
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_POSITION] == 80


async def test_close_cover_tilt(opp, setup_comp):
    """Test closing the cover tilt."""
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 50
    await opp.services.async_call(
        DOMAIN, SERVICE_CLOSE_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0


async def test_open_cover_tilt(opp, setup_comp):
    """Test opening the cover tilt."""
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 50
    await opp.services.async_call(
        DOMAIN, SERVICE_OPEN_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100


async def test_toggle_cover_tilt(opp, setup_comp):
    """Test toggling the cover tilt."""
    # Start open
    await opp.services.async_call(
        DOMAIN, SERVICE_OPEN_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100
    # Toggle closed
    await opp.services.async_call(
        DOMAIN, SERVICE_TOGGLE_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0
    # Toggle Open
    await opp.services.async_call(
        DOMAIN, SERVICE_TOGGLE_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    for _ in range(10):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100


async def test_set_cover_tilt_position(opp, setup_comp):
    """Test moving the cover til to a specific position."""
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 50
    await opp.services.async_call(
        DOMAIN,
        SERVICE_SET_COVER_TILT_POSITION,
        {ATTR_ENTITY_ID: ENTITY_COVER, ATTR_TILT_POSITION: 90},
        blocking=True,
    )
    for _ in range(7):
        future = dt_util.utcnow() + timedelta(seconds=1)
        async_fire_time_changed(opp, future)
        await opp.async_block_till_done()

    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 90


async def test_stop_cover_tilt(opp, setup_comp):
    """Test stopping the cover tilt."""
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 50
    await opp.services.async_call(
        DOMAIN, SERVICE_CLOSE_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    future = dt_util.utcnow() + timedelta(seconds=1)
    async_fire_time_changed(opp, future)
    await opp.async_block_till_done()
    await opp.services.async_call(
        DOMAIN, SERVICE_STOP_COVER_TILT, {ATTR_ENTITY_ID: ENTITY_COVER}, blocking=True
    )
    async_fire_time_changed(opp, future)
    await opp.async_block_till_done()
    state = opp.states.get(ENTITY_COVER)
    assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 40
