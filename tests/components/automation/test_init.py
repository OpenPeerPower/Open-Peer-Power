"""The tests for the automation component."""
from datetime import timedelta
from unittest.mock import Mock, patch

import pytest

import openpeerpower.components.automation as automation
from openpeerpower.components.automation import DOMAIN
from openpeerpower.const import (
    ATTR_ENTITY_ID,
    ATTR_NAME,
    EVENT_AUTOMATION_TRIGGERED,
    EVENT_OPENPEERPOWER_START,
    STATE_OFF,
    STATE_ON,
)
from openpeerpower.core import Context, CoreState, State
from openpeerpower.exceptions import OpenPeerPowerError, Unauthorized
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    assert_setup_component,
    async_fire_time_changed,
    async_mock_service,
    mock_restore_cache,
)
from tests.components.automation import common


@pytest.fixture
def calls(opp):
    """Track calls to a mock service."""
    return async_mock_service(opp, "test", "automation")


async def test_service_data_not_a_dict(opp, calls):
    """Test service data not dict."""
    with assert_setup_component(0, automation.DOMAIN):
        assert await async_setup_component(
            opp,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "action": {"service": "test.automation", "data": 100},
                }
            },
        )


async def test_service_specify_data(opp, calls):
    """Test service data."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.platform }} - "
                        "{{ trigger.event.event_type }}"
                    },
                },
            }
        },
    )

    time = dt_util.utcnow()

    with patch("openpeerpower.components.automation.utcnow", return_value=time):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["some"] == "event - test_event"
    state = opp.states.get("automation.hello")
    assert state is not None
    assert state.attributes.get("last_triggered") == time


async def test_action_delay(opp, calls):
    """Test action delay."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": [
                    {
                        "service": "test.automation",
                        "data_template": {
                            "some": "{{ trigger.platform }} - "
                            "{{ trigger.event.event_type }}"
                        },
                    },
                    {"delay": {"minutes": "10"}},
                    {
                        "service": "test.automation",
                        "data_template": {
                            "some": "{{ trigger.platform }} - "
                            "{{ trigger.event.event_type }}"
                        },
                    },
                ],
            }
        },
    )

    time = dt_util.utcnow()

    with patch("openpeerpower.components.automation.utcnow", return_value=time):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["some"] == "event - test_event"

    future = dt_util.utcnow() + timedelta(minutes=10)
    async_fire_time_changed(opp, future)
    await opp.async_block_till_done()

    assert len(calls) == 2
    assert calls[1].data["some"] == "event - test_event"

    state = opp.states.get("automation.hello")
    assert state is not None
    assert state.attributes.get("last_triggered") == time


async def test_service_specify_entity_id(opp, calls):
    """Test service data."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert ["hello.world"] == calls[0].data.get(ATTR_ENTITY_ID)


async def test_service_specify_entity_id_list(opp, calls):
    """Test service data."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {
                    "service": "test.automation",
                    "entity_id": ["hello.world", "hello.world2"],
                },
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert ["hello.world", "hello.world2"] == calls[0].data.get(ATTR_ENTITY_ID)


async def test_two_triggers(opp, calls):
    """Test triggers."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": [
                    {"platform": "event", "event_type": "test_event"},
                    {"platform": "state", "entity_id": "test.entity"},
                ],
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)
    opp.states.async_set("test.entity", "hello")
    await opp.async_block_till_done()
    assert 2 == len(calls)


async def test_trigger_service_ignoring_condition(opp, calls):
    """Test triggers."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "test",
                "trigger": [{"platform": "event", "event_type": "test_event"}],
                "condition": {
                    "condition": "state",
                    "entity_id": "non.existing",
                    "state": "beer",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 0

    await opp.services.async_call(
        "automation", "trigger", {"entity_id": "automation.test"}, blocking=True
    )
    assert len(calls) == 1

    await opp.services.async_call(
        "automation",
        "trigger",
        {"entity_id": "automation.test", "skip_condition": True},
        blocking=True,
    )
    assert len(calls) == 2

    await opp.services.async_call(
        "automation",
        "trigger",
        {"entity_id": "automation.test", "skip_condition": False},
        blocking=True,
    )
    assert len(calls) == 2


async def test_two_conditions_with_and(opp, calls):
    """Test two and conditions."""
    entity_id = "test.entity"
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": [{"platform": "event", "event_type": "test_event"}],
                "condition": [
                    {"condition": "state", "entity_id": entity_id, "state": "100"},
                    {
                        "condition": "numeric_state",
                        "entity_id": entity_id,
                        "below": 150,
                    },
                ],
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set(entity_id, 100)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)

    opp.states.async_set(entity_id, 101)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)

    opp.states.async_set(entity_id, 151)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_automation_list_setting(opp, calls):
    """Event is not a valid condition."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "action": {"service": "test.automation"},
                },
                {
                    "trigger": {"platform": "event", "event_type": "test_event_2"},
                    "action": {"service": "test.automation"},
                },
            ]
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)

    opp.bus.async_fire("test_event_2")
    await opp.async_block_till_done()
    assert 2 == len(calls)


async def test_automation_calling_two_actions(opp, calls):
    """Test if we can call two actions from automation async definition."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": [
                    {"service": "test.automation", "data": {"position": 0}},
                    {"service": "test.automation", "data": {"position": 1}},
                ],
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert len(calls) == 2
    assert calls[0].data["position"] == 0
    assert calls[1].data["position"] == 1


async def test_shared_context(opp, calls):
    """Test that the shared context is passed down the chain."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "alias": "hello",
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "action": {"event": "test_event2"},
                },
                {
                    "alias": "bye",
                    "trigger": {"platform": "event", "event_type": "test_event2"},
                    "action": {"service": "test.automation"},
                },
            ]
        },
    )

    context = Context()
    first_automation_listener = Mock()
    event_mock = Mock()

    opp.bus.async_listen("test_event2", first_automation_listener)
    opp.bus.async_listen(EVENT_AUTOMATION_TRIGGERED, event_mock)
    opp.bus.async_fire("test_event", context=context)
    await opp.async_block_till_done()

    # Ensure events was fired
    assert first_automation_listener.call_count == 1
    assert event_mock.call_count == 2

    # Verify automation triggered evenet for 'hello' automation
    args, kwargs = event_mock.call_args_list[0]
    first_trigger_context = args[0].context
    assert first_trigger_context.parent_id == context.id
    # Ensure event data has all attributes set
    assert args[0].data.get(ATTR_NAME) is not None
    assert args[0].data.get(ATTR_ENTITY_ID) is not None

    # Ensure context set correctly for event fired by 'hello' automation
    args, kwargs = first_automation_listener.call_args
    assert args[0].context is first_trigger_context

    # Ensure the 'hello' automation state has the right context
    state = opp.states.get("automation.hello")
    assert state is not None
    assert state.context is first_trigger_context

    # Verify automation triggered evenet for 'bye' automation
    args, kwargs = event_mock.call_args_list[1]
    second_trigger_context = args[0].context
    assert second_trigger_context.parent_id == first_trigger_context.id
    # Ensure event data has all attributes set
    assert args[0].data.get(ATTR_NAME) is not None
    assert args[0].data.get(ATTR_ENTITY_ID) is not None

    # Ensure the service call from the second automation
    # shares the same context
    assert len(calls) == 1
    assert calls[0].context is second_trigger_context


async def test_services(opp, calls):
    """Test the automation services for turning entities on/off."""
    entity_id = "automation.hello"

    assert opp.states.get(entity_id) is None
    assert not automation.is_on(opp, entity_id)

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation"},
            }
        },
    )

    assert opp.states.get(entity_id) is not None
    assert automation.is_on(opp, entity_id)

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1

    await common.async_turn_off(opp, entity_id)
    await opp.async_block_till_done()

    assert not automation.is_on(opp, entity_id)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1

    await common.async_toggle(opp, entity_id)
    await opp.async_block_till_done()

    assert automation.is_on(opp, entity_id)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 2

    await common.async_trigger(opp, entity_id)
    await opp.async_block_till_done()
    assert len(calls) == 3

    await common.async_turn_off(opp, entity_id)
    await opp.async_block_till_done()
    await common.async_trigger(opp, entity_id)
    await opp.async_block_till_done()
    assert len(calls) == 4

    await common.async_turn_on(opp, entity_id)
    await opp.async_block_till_done()
    assert automation.is_on(opp, entity_id)


async def test_reload_config_service(opp, calls, opp_admin_user, opp_read_only_user):
    """Test the reload config service."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {
                    "service": "test.automation",
                    "data_template": {"event": "{{ trigger.event.event_type }}"},
                },
            }
        },
    )
    assert opp.states.get("automation.hello") is not None
    assert opp.states.get("automation.bye") is None
    listeners = opp.bus.async_listeners()
    assert listeners.get("test_event") == 1
    assert listeners.get("test_event2") is None

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data.get("event") == "test_event"

    with patch(
        "openpeerpower.config.load_yaml_config_file",
        autospec=True,
        return_value={
            automation.DOMAIN: {
                "alias": "bye",
                "trigger": {"platform": "event", "event_type": "test_event2"},
                "action": {
                    "service": "test.automation",
                    "data_template": {"event": "{{ trigger.event.event_type }}"},
                },
            }
        },
    ):
        with pytest.raises(Unauthorized):
            await common.async_reload(opp, Context(user_id=opp_read_only_user.id))
            await opp.async_block_till_done()
        await common.async_reload(opp, Context(user_id=opp_admin_user.id))
        await opp.async_block_till_done()
        # De-flake ?!
        await opp.async_block_till_done()

    assert opp.states.get("automation.hello") is None
    assert opp.states.get("automation.bye") is not None
    listeners = opp.bus.async_listeners()
    assert listeners.get("test_event") is None
    assert listeners.get("test_event2") == 1

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1

    opp.bus.async_fire("test_event2")
    await opp.async_block_till_done()
    assert len(calls) == 2
    assert calls[1].data.get("event") == "test_event2"


async def test_reload_config_when_invalid_config(opp, calls):
    """Test the reload config service handling invalid config."""
    with assert_setup_component(1, automation.DOMAIN):
        assert await async_setup_component(
            opp,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "alias": "hello",
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "action": {
                        "service": "test.automation",
                        "data_template": {"event": "{{ trigger.event.event_type }}"},
                    },
                }
            },
        )
    assert opp.states.get("automation.hello") is not None

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data.get("event") == "test_event"

    with patch(
        "openpeerpower.config.load_yaml_config_file",
        autospec=True,
        return_value={automation.DOMAIN: "not valid"},
    ):
        await common.async_reload(opp)
        await opp.async_block_till_done()

    assert opp.states.get("automation.hello") is None

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1


async def test_reload_config_handles_load_fails(opp, calls):
    """Test the reload config service."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {
                    "service": "test.automation",
                    "data_template": {"event": "{{ trigger.event.event_type }}"},
                },
            }
        },
    )
    assert opp.states.get("automation.hello") is not None

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data.get("event") == "test_event"

    with patch(
        "openpeerpower.config.load_yaml_config_file",
        side_effect=OpenPeerPowerError("bla"),
    ):
        await common.async_reload(opp)
        await opp.async_block_till_done()

    assert opp.states.get("automation.hello") is not None

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 2


async def test_automation_restore_state(opp):
    """Ensure states are restored on startup."""
    time = dt_util.utcnow()

    mock_restore_cache(
        opp,
        (
            State("automation.hello", STATE_ON),
            State("automation.bye", STATE_OFF, {"last_triggered": time}),
        ),
    )

    config = {
        automation.DOMAIN: [
            {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event_hello"},
                "action": {"service": "test.automation"},
            },
            {
                "alias": "bye",
                "trigger": {"platform": "event", "event_type": "test_event_bye"},
                "action": {"service": "test.automation"},
            },
        ]
    }

    assert await async_setup_component(opp, automation.DOMAIN, config)

    state = opp.states.get("automation.hello")
    assert state
    assert state.state == STATE_ON
    assert state.attributes["last_triggered"] is None

    state = opp.states.get("automation.bye")
    assert state
    assert state.state == STATE_OFF
    assert state.attributes["last_triggered"] == time

    calls = async_mock_service(opp, "test", "automation")

    assert automation.is_on(opp, "automation.bye") is False

    opp.bus.async_fire("test_event_bye")
    await opp.async_block_till_done()
    assert len(calls) == 0

    assert automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event_hello")
    await opp.async_block_till_done()

    assert len(calls) == 1


async def test_initial_value_off(opp):
    """Test initial value off."""
    calls = async_mock_service(opp, "test", "automation")

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "initial_state": "off",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    assert not automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 0


async def test_initial_value_on(opp):
    """Test initial value on."""
    opp.state = CoreState.not_running
    calls = async_mock_service(opp, "test", "automation")

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "initial_state": "on",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {
                    "service": "test.automation",
                    "entity_id": ["hello.world", "hello.world2"],
                },
            }
        },
    )
    assert automation.is_on(opp, "automation.hello")

    await opp.async_start()
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1


async def test_initial_value_off_but_restore_on(opp):
    """Test initial value off and restored state is turned on."""
    opp.state = CoreState.not_running
    calls = async_mock_service(opp, "test", "automation")
    mock_restore_cache(opp, (State("automation.hello", STATE_ON),))

    await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "initial_state": "off",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    assert not automation.is_on(opp, "automation.hello")

    await opp.async_start()
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 0


async def test_initial_value_on_but_restore_off(opp):
    """Test initial value on and restored state is turned off."""
    calls = async_mock_service(opp, "test", "automation")
    mock_restore_cache(opp, (State("automation.hello", STATE_OFF),))

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "initial_state": "on",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    assert automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1


async def test_no_initial_value_and_restore_off(opp):
    """Test initial value off and restored state is turned on."""
    calls = async_mock_service(opp, "test", "automation")
    mock_restore_cache(opp, (State("automation.hello", STATE_OFF),))

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    assert not automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 0


async def test_automation_is_on_if_no_initial_state_or_restore(opp):
    """Test initial value is on when no initial state or restored state."""
    calls = async_mock_service(opp, "test", "automation")

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    assert automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 1


async def test_automation_not_trigger_on_bootstrap(opp):
    """Test if automation is not trigger on bootstrap."""
    opp.state = CoreState.not_running
    calls = async_mock_service(opp, "test", "automation")

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )
    assert automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert len(calls) == 0

    opp.bus.async_fire(EVENT_OPENPEERPOWER_START)
    await opp.async_block_till_done()
    assert automation.is_on(opp, "automation.hello")

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert len(calls) == 1
    assert ["hello.world"] == calls[0].data.get(ATTR_ENTITY_ID)


async def test_automation_with_error_in_script(opp, caplog):
    """Test automation with an error in script."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation", "entity_id": "hello.world"},
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert "Service not found" in caplog.text


async def test_automation_with_error_in_script_2(opp, caplog):
    """Test automation with an error in script."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": None, "entity_id": "hello.world"},
            }
        },
    )

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert "string value is None" in caplog.text


async def test_automation_restore_last_triggered_with_initial_state(opp):
    """Ensure last_triggered is restored, even when initial state is set."""
    time = dt_util.utcnow()

    mock_restore_cache(
        opp,
        (
            State("automation.hello", STATE_ON),
            State("automation.bye", STATE_ON, {"last_triggered": time}),
            State("automation.solong", STATE_OFF, {"last_triggered": time}),
        ),
    )

    config = {
        automation.DOMAIN: [
            {
                "alias": "hello",
                "initial_state": "off",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation"},
            },
            {
                "alias": "bye",
                "initial_state": "off",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation"},
            },
            {
                "alias": "solong",
                "initial_state": "on",
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation"},
            },
        ]
    }

    await async_setup_component(opp, automation.DOMAIN, config)

    state = opp.states.get("automation.hello")
    assert state
    assert state.state == STATE_OFF
    assert state.attributes["last_triggered"] is None

    state = opp.states.get("automation.bye")
    assert state
    assert state.state == STATE_OFF
    assert state.attributes["last_triggered"] == time

    state = opp.states.get("automation.solong")
    assert state
    assert state.state == STATE_ON
    assert state.attributes["last_triggered"] == time


async def test_extraction_functions(opp):
    """Test extraction functions."""
    assert await async_setup_component(
        opp,
        DOMAIN,
        {
            DOMAIN: [
                {
                    "alias": "test1",
                    "trigger": {"platform": "state", "entity_id": "sensor.trigger_1"},
                    "condition": {
                        "condition": "state",
                        "entity_id": "light.condition_state",
                        "state": "on",
                    },
                    "action": [
                        {
                            "service": "test.script",
                            "data": {"entity_id": "light.in_both"},
                        },
                        {
                            "service": "test.script",
                            "data": {"entity_id": "light.in_first"},
                        },
                        {
                            "domain": "light",
                            "device_id": "device-in-both",
                            "entity_id": "light.bla",
                            "type": "turn_on",
                        },
                    ],
                },
                {
                    "alias": "test2",
                    "trigger": {
                        "platform": "device",
                        "domain": "light",
                        "type": "turned_on",
                        "entity_id": "light.trigger_2",
                        "device_id": "trigger-device-2",
                    },
                    "condition": {
                        "condition": "device",
                        "device_id": "condition-device",
                        "domain": "light",
                        "type": "is_on",
                        "entity_id": "light.bla",
                    },
                    "action": [
                        {
                            "service": "test.script",
                            "data": {"entity_id": "light.in_both"},
                        },
                        {
                            "condition": "state",
                            "entity_id": "sensor.condition",
                            "state": "100",
                        },
                        {"scene": "scene.hello"},
                        {
                            "domain": "light",
                            "device_id": "device-in-both",
                            "entity_id": "light.bla",
                            "type": "turn_on",
                        },
                        {
                            "domain": "light",
                            "device_id": "device-in-last",
                            "entity_id": "light.bla",
                            "type": "turn_on",
                        },
                    ],
                },
            ]
        },
    )

    assert set(automation.automations_with_entity(opp, "light.in_both")) == {
        "automation.test1",
        "automation.test2",
    }
    assert set(automation.entities_in_automation(opp, "automation.test1")) == {
        "sensor.trigger_1",
        "light.condition_state",
        "light.in_both",
        "light.in_first",
    }
    assert set(automation.automations_with_device(opp, "device-in-both")) == {
        "automation.test1",
        "automation.test2",
    }
    assert set(automation.devices_in_automation(opp, "automation.test2")) == {
        "trigger-device-2",
        "condition-device",
        "device-in-both",
        "device-in-last",
    }
