"""The tests for the Event automation."""
import pytest

import openpeerpower.components.automation as automation
from openpeerpower.core import Context
from openpeerpower.setup import async_setup_component

from tests.common import async_mock_service, mock_component
from tests.components.automation import common


@pytest.fixture
def calls(opp):
    """Track calls to a mock service."""
    return async_mock_service(opp, "test", "automation")


@pytest.fixture(autouse=True)
def setup_comp(opp):
    """Initialize components."""
    mock_component(opp, "group")


async def test_if_fires_on_event(opp, calls):
    """Test the firing of events."""
    context = Context()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event", context=context)
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert calls[0].context.parent_id == context.id

    await common.async_turn_off(opp)
    await opp.async_block_till_done()

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_event_extra_data(opp, calls):
    """Test the firing of events still matches with event data."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event", {"extra_key": "extra_data"})
    await opp.async_block_till_done()
    assert 1 == len(calls)

    await common.async_turn_off(opp)
    await opp.async_block_till_done()

    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_event_with_data(opp, calls):
    """Test the firing of events with data."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "event",
                    "event_type": "test_event",
                    "event_data": {"some_attr": "some_value"},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event", {"some_attr": "some_value", "another": "value"})
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_event_with_empty_data_config(opp, calls):
    """Test the firing of events with empty data config.

    The frontend automation editor can produce configurations with an
    empty dict for event_data instead of no key.
    """
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "event",
                    "event_type": "test_event",
                    "event_data": {},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event", {"some_attr": "some_value", "another": "value"})
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_event_with_nested_data(opp, calls):
    """Test the firing of events with nested data."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "event",
                    "event_type": "test_event",
                    "event_data": {"parent_attr": {"some_attr": "some_value"}},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire(
        "test_event", {"parent_attr": {"some_attr": "some_value", "another": "value"}}
    )
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_fires_if_event_data_not_matches(opp, calls):
    """Test firing of event if no match."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "event",
                    "event_type": "test_event",
                    "event_data": {"some_attr": "some_value"},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.bus.async_fire("test_event", {"some_attr": "some_other_value"})
    await opp.async_block_till_done()
    assert 0 == len(calls)
