"""The tests for local file camera component."""
from unittest.mock import mock_open, patch

import pytest

from openpeerpower.components import camera
from openpeerpower.components.camera import STATE_IDLE, STATE_STREAMING
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.setup import async_setup_component

from tests.components.camera import common


@pytest.fixture
def demo_camera(opp):
    """Initialize a demo camera platform."""
    opp.loop.run_until_complete(
        async_setup_component(opp, "camera", {camera.DOMAIN: {"platform": "demo"}})
    )
    return opp.data["camera"].get_entity("camera.demo_camera")


async def test_init_state_is_streaming(opp, demo_camera):
    """Demo camera initialize as streaming."""
    assert demo_camera.state == STATE_STREAMING

    mock_on_img = mock_open(read_data=b"ON")
    with patch("openpeerpower.components.demo.camera.open", mock_on_img, create=True):
        image = await camera.async_get_image(opp, demo_camera.entity_id)
        assert mock_on_img.called
        assert mock_on_img.call_args_list[0][0][0][-6:] in [
            "_0.jpg",
            "_1.jpg",
            "_2.jpg",
            "_3.jpg",
        ]
        assert image.content == b"ON"


async def test_turn_on_state_back_to_streaming(opp, demo_camera):
    """After turn on state back to streaming."""
    assert demo_camera.state == STATE_STREAMING
    await common.async_turn_off(opp, demo_camera.entity_id)
    await opp.async_block_till_done()

    assert demo_camera.state == STATE_IDLE

    await common.async_turn_on(opp, demo_camera.entity_id)
    await opp.async_block_till_done()

    assert demo_camera.state == STATE_STREAMING


async def test_turn_off_image(opp, demo_camera):
    """After turn off, Demo camera raise error."""
    await common.async_turn_off(opp, demo_camera.entity_id)
    await opp.async_block_till_done()

    with pytest.raises(OpenPeerPowerError) as error:
        await camera.async_get_image(opp, demo_camera.entity_id)
        assert error.args[0] == "Camera is off"


async def test_turn_off_invalid_camera(opp, demo_camera):
    """Turn off non-exist camera should quietly fail."""
    assert demo_camera.state == STATE_STREAMING
    await common.async_turn_off(opp, "camera.invalid_camera")
    await opp.async_block_till_done()

    assert demo_camera.state == STATE_STREAMING


async def test_motion_detection(opp):
    """Test motion detection services."""
    # Setup platform
    await async_setup_component(opp, "camera", {"camera": {"platform": "demo"}})

    # Fetch state and check motion detection attribute
    state = opp.states.get("camera.demo_camera")
    assert not state.attributes.get("motion_detection")

    # Call service to turn on motion detection
    common.enable_motion_detection(opp, "camera.demo_camera")
    await opp.async_block_till_done()

    # Check if state has been updated.
    state = opp.states.get("camera.demo_camera")
    assert state.attributes.get("motion_detection")
