"""Tests for the light intents."""
from openpeerpower.components import light
from openpeerpower.components.light import intent
from openpeerpower.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, SERVICE_TURN_ON
from openpeerpower.helpers.intent import IntentHandleError

from tests.common import async_mock_service


async def test_intent_set_color(opp):
    """Test the set color intent."""
    opp.states.async_set(
        "light.hello_2", "off", {ATTR_SUPPORTED_FEATURES: light.SUPPORT_COLOR}
    )
    opp.states.async_set("switch.hello", "off")
    calls = async_mock_service(opp, light.DOMAIN, light.SERVICE_TURN_ON)
    await intent.async_setup_intents(opp)

    result = await opp.helpers.intent.async_handle(
        "test",
        intent.INTENT_SET,
        {"name": {"value": "Hello"}, "color": {"value": "blue"}},
    )
    await opp.async_block_till_done()

    assert result.speech["plain"]["speech"] == "Changed hello 2 to the color blue"

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data.get(ATTR_ENTITY_ID) == "light.hello_2"
    assert call.data.get(light.ATTR_RGB_COLOR) == (0, 0, 255)


async def test_intent_set_color_tests_feature(opp):
    """Test the set color intent."""
    opp.states.async_set("light.hello", "off")
    calls = async_mock_service(opp, light.DOMAIN, light.SERVICE_TURN_ON)
    await intent.async_setup_intents(opp)

    try:
        await opp.helpers.intent.async_handle(
            "test",
            intent.INTENT_SET,
            {"name": {"value": "Hello"}, "color": {"value": "blue"}},
        )
        assert False, "handling intent should have raised"
    except IntentHandleError as err:
        assert str(err) == "Entity hello does not support changing colors"

    assert len(calls) == 0


async def test_intent_set_color_and_brightness(opp):
    """Test the set color intent."""
    opp.states.async_set(
        "light.hello_2",
        "off",
        {ATTR_SUPPORTED_FEATURES: (light.SUPPORT_COLOR | light.SUPPORT_BRIGHTNESS)},
    )
    opp.states.async_set("switch.hello", "off")
    calls = async_mock_service(opp, light.DOMAIN, light.SERVICE_TURN_ON)
    await intent.async_setup_intents(opp)

    result = await opp.helpers.intent.async_handle(
        "test",
        intent.INTENT_SET,
        {
            "name": {"value": "Hello"},
            "color": {"value": "blue"},
            "brightness": {"value": "20"},
        },
    )
    await opp.async_block_till_done()

    assert (
        result.speech["plain"]["speech"]
        == "Changed hello 2 to the color blue and 20% brightness"
    )

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == light.DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data.get(ATTR_ENTITY_ID) == "light.hello_2"
    assert call.data.get(light.ATTR_RGB_COLOR) == (0, 0, 255)
    assert call.data.get(light.ATTR_BRIGHTNESS_PCT) == 20
