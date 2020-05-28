"""The tests for the Light Switch platform."""

from openpeerpower.setup import async_setup_component

from tests.components.light import common
from tests.components.switch import common as switch_common


async def test_default_state(opp):
    """Test light switch default state."""
    await async_setup_component(
        opp,
        "light",
        {
            "light": {
                "platform": "switch",
                "entity_id": "switch.test",
                "name": "Christmas Tree Lights",
            }
        },
    )
    await opp.async_block_till_done()

    state = opp.states.get("light.christmas_tree_lights")
    assert state is not None
    assert state.state == "unavailable"
    assert state.attributes["supported_features"] == 0
    assert state.attributes.get("brightness") is None
    assert state.attributes.get("hs_color") is None
    assert state.attributes.get("color_temp") is None
    assert state.attributes.get("white_value") is None
    assert state.attributes.get("effect_list") is None
    assert state.attributes.get("effect") is None


async def test_light_service_calls(opp):
    """Test service calls to light."""
    await async_setup_component(opp, "switch", {"switch": [{"platform": "demo"}]})
    await async_setup_component(
        opp,
        "light",
        {"light": [{"platform": "switch", "entity_id": "switch.decorative_lights"}]},
    )
    await opp.async_block_till_done()

    assert opp.states.get("light.light_switch").state == "on"

    await common.async_toggle(opp, "light.light_switch")

    assert opp.states.get("switch.decorative_lights").state == "off"
    assert opp.states.get("light.light_switch").state == "off"

    await common.async_turn_on(opp, "light.light_switch")

    assert opp.states.get("switch.decorative_lights").state == "on"
    assert opp.states.get("light.light_switch").state == "on"

    await common.async_turn_off(opp, "light.light_switch")

    assert opp.states.get("switch.decorative_lights").state == "off"
    assert opp.states.get("light.light_switch").state == "off"


async def test_switch_service_calls(opp):
    """Test service calls to switch."""
    await async_setup_component(opp, "switch", {"switch": [{"platform": "demo"}]})
    await async_setup_component(
        opp,
        "light",
        {"light": [{"platform": "switch", "entity_id": "switch.decorative_lights"}]},
    )
    await opp.async_block_till_done()

    assert opp.states.get("light.light_switch").state == "on"

    await switch_common.async_turn_off(opp, "switch.decorative_lights")

    assert opp.states.get("switch.decorative_lights").state == "off"
    assert opp.states.get("light.light_switch").state == "off"

    await switch_common.async_turn_on(opp, "switch.decorative_lights")

    assert opp.states.get("switch.decorative_lights").state == "on"
    assert opp.states.get("light.light_switch").state == "on"
