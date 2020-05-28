"""Test reproduce state for Light."""
from openpeerpower.components.light.reproduce_state import DEPRECATION_WARNING
from openpeerpower.core import State

from tests.common import async_mock_service

VALID_BRIGHTNESS = {"brightness": 180}
VALID_WHITE_VALUE = {"white_value": 200}
VALID_FLASH = {"flash": "short"}
VALID_EFFECT = {"effect": "random"}
VALID_TRANSITION = {"transition": 15}
VALID_COLOR_NAME = {"color_name": "red"}
VALID_COLOR_TEMP = {"color_temp": 240}
VALID_HS_COLOR = {"hs_color": (345, 75)}
VALID_KELVIN = {"kelvin": 4000}
VALID_PROFILE = {"profile": "relax"}
VALID_RGB_COLOR = {"rgb_color": (255, 63, 111)}
VALID_XY_COLOR = {"xy_color": (0.59, 0.274)}


async def test_reproducing_states(opp, caplog):
    """Test reproducing Light states."""
    opp.states.async_set("light.entity_off", "off", {})
    opp.states.async_set("light.entity_bright", "on", VALID_BRIGHTNESS)
    opp.states.async_set("light.entity_white", "on", VALID_WHITE_VALUE)
    opp.states.async_set("light.entity_flash", "on", VALID_FLASH)
    opp.states.async_set("light.entity_effect", "on", VALID_EFFECT)
    opp.states.async_set("light.entity_trans", "on", VALID_TRANSITION)
    opp.states.async_set("light.entity_name", "on", VALID_COLOR_NAME)
    opp.states.async_set("light.entity_temp", "on", VALID_COLOR_TEMP)
    opp.states.async_set("light.entity_hs", "on", VALID_HS_COLOR)
    opp.states.async_set("light.entity_kelvin", "on", VALID_KELVIN)
    opp.states.async_set("light.entity_profile", "on", VALID_PROFILE)
    opp.states.async_set("light.entity_rgb", "on", VALID_RGB_COLOR)
    opp.states.async_set("light.entity_xy", "on", VALID_XY_COLOR)

    turn_on_calls = async_mock_service(opp, "light", "turn_on")
    turn_off_calls = async_mock_service(opp, "light", "turn_off")

    # These calls should do nothing as entities already in desired state
    await opp.helpers.state.async_reproduce_state(
        [
            State("light.entity_off", "off"),
            State("light.entity_bright", "on", VALID_BRIGHTNESS),
            State("light.entity_white", "on", VALID_WHITE_VALUE),
            State("light.entity_flash", "on", VALID_FLASH),
            State("light.entity_effect", "on", VALID_EFFECT),
            State("light.entity_trans", "on", VALID_TRANSITION),
            State("light.entity_name", "on", VALID_COLOR_NAME),
            State("light.entity_temp", "on", VALID_COLOR_TEMP),
            State("light.entity_hs", "on", VALID_HS_COLOR),
            State("light.entity_kelvin", "on", VALID_KELVIN),
            State("light.entity_profile", "on", VALID_PROFILE),
            State("light.entity_rgb", "on", VALID_RGB_COLOR),
            State("light.entity_xy", "on", VALID_XY_COLOR),
        ],
        blocking=True,
    )

    assert len(turn_on_calls) == 0
    assert len(turn_off_calls) == 0

    # Test invalid state is handled
    await opp.helpers.state.async_reproduce_state(
        [State("light.entity_off", "not_supported")], blocking=True
    )

    assert "not_supported" in caplog.text
    assert len(turn_on_calls) == 0
    assert len(turn_off_calls) == 0

    # Make sure correct services are called
    await opp.helpers.state.async_reproduce_state(
        [
            State("light.entity_xy", "off"),
            State("light.entity_off", "on", VALID_BRIGHTNESS),
            State("light.entity_bright", "on", VALID_WHITE_VALUE),
            State("light.entity_white", "on", VALID_FLASH),
            State("light.entity_flash", "on", VALID_EFFECT),
            State("light.entity_effect", "on", VALID_TRANSITION),
            State("light.entity_trans", "on", VALID_COLOR_NAME),
            State("light.entity_name", "on", VALID_COLOR_TEMP),
            State("light.entity_temp", "on", VALID_HS_COLOR),
            State("light.entity_hs", "on", VALID_KELVIN),
            State("light.entity_kelvin", "on", VALID_PROFILE),
            State("light.entity_profile", "on", VALID_RGB_COLOR),
            State("light.entity_rgb", "on", VALID_XY_COLOR),
        ],
        blocking=True,
    )

    assert len(turn_on_calls) == 12

    expected_calls = []

    expected_off = VALID_BRIGHTNESS
    expected_off["entity_id"] = "light.entity_off"
    expected_calls.append(expected_off)

    expected_bright = VALID_WHITE_VALUE
    expected_bright["entity_id"] = "light.entity_bright"
    expected_calls.append(expected_bright)

    expected_white = VALID_FLASH
    expected_white["entity_id"] = "light.entity_white"
    expected_calls.append(expected_white)

    expected_flash = VALID_EFFECT
    expected_flash["entity_id"] = "light.entity_flash"
    expected_calls.append(expected_flash)

    expected_effect = VALID_TRANSITION
    expected_effect["entity_id"] = "light.entity_effect"
    expected_calls.append(expected_effect)

    expected_trans = VALID_COLOR_NAME
    expected_trans["entity_id"] = "light.entity_trans"
    expected_calls.append(expected_trans)

    expected_name = VALID_COLOR_TEMP
    expected_name["entity_id"] = "light.entity_name"
    expected_calls.append(expected_name)

    expected_temp = VALID_HS_COLOR
    expected_temp["entity_id"] = "light.entity_temp"
    expected_calls.append(expected_temp)

    expected_hs = VALID_KELVIN
    expected_hs["entity_id"] = "light.entity_hs"
    expected_calls.append(expected_hs)

    expected_kelvin = VALID_PROFILE
    expected_kelvin["entity_id"] = "light.entity_kelvin"
    expected_calls.append(expected_kelvin)

    expected_profile = VALID_RGB_COLOR
    expected_profile["entity_id"] = "light.entity_profile"
    expected_calls.append(expected_profile)

    expected_rgb = VALID_XY_COLOR
    expected_rgb["entity_id"] = "light.entity_rgb"
    expected_calls.append(expected_rgb)

    for call in turn_on_calls:
        assert call.domain == "light"
        found = False
        for expected in expected_calls:
            if call.data["entity_id"] == expected["entity_id"]:
                # We found the matching entry
                assert call.data == expected
                found = True
                break
        # No entry found
        assert found

    assert len(turn_off_calls) == 1
    assert turn_off_calls[0].domain == "light"
    assert turn_off_calls[0].data == {"entity_id": "light.entity_xy"}


async def test_deprecation_warning(opp, caplog):
    """Test deprecation warning."""
    opp.states.async_set("light.entity_off", "off", {})
    turn_on_calls = async_mock_service(opp, "light", "turn_on")
    await opp.helpers.state.async_reproduce_state(
        [State("light.entity_off", "on", {"brightness_pct": 80})], blocking=True
    )
    assert len(turn_on_calls) == 1
    assert DEPRECATION_WARNING in caplog.text
