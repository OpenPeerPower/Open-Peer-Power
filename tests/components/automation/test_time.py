"""The tests for the time automation."""
from datetime import timedelta
from unittest.mock import patch

import pytest

import openpeerpower.components.automation as automation
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    assert_setup_component,
    async_fire_time_changed,
    async_mock_service,
    mock_component,
)


@pytest.fixture
def calls(opp):
    """Track calls to a mock service."""
    return async_mock_service(opp, "test", "automation")


@pytest.fixture(autouse=True)
def setup_comp(opp):
    """Initialize components."""
    mock_component(opp, "group")


async def test_if_fires_using_at(opp, calls):
    """Test for firing at."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "time", "at": "5:00:00"},
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.platform }} - {{ trigger.now.hour }}"
                    },
                },
            }
        },
    )

    async_fire_time_changed(opp, dt_util.utcnow().replace(hour=5, minute=0, second=0))

    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert "time - 5" == calls[0].data["some"]


async def test_if_not_fires_using_wrong_at(opp, calls):
    """YAML translates time values to total seconds.

    This should break the before rule.
    """
    with assert_setup_component(0, automation.DOMAIN):
        assert await async_setup_component(
            opp,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {
                        "platform": "time",
                        "at": 3605,
                        # Total seconds. Hour = 3600 second
                    },
                    "action": {"service": "test.automation"},
                }
            },
        )

    async_fire_time_changed(opp, dt_util.utcnow().replace(hour=1, minute=0, second=5))

    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_action_before(opp, calls):
    """Test for if action before."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": {"condition": "time", "before": "10:00"},
                "action": {"service": "test.automation"},
            }
        },
    )

    before_10 = dt_util.now().replace(hour=8)
    after_10 = dt_util.now().replace(hour=14)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=before_10):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 1 == len(calls)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=after_10):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 1 == len(calls)


async def test_if_action_after(opp, calls):
    """Test for if action after."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": {"condition": "time", "after": "10:00"},
                "action": {"service": "test.automation"},
            }
        },
    )

    before_10 = dt_util.now().replace(hour=8)
    after_10 = dt_util.now().replace(hour=14)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=before_10):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 0 == len(calls)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=after_10):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 1 == len(calls)


async def test_if_action_one_weekday(opp, calls):
    """Test for if action with one weekday."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": {"condition": "time", "weekday": "mon"},
                "action": {"service": "test.automation"},
            }
        },
    )

    days_past_monday = dt_util.now().weekday()
    monday = dt_util.now() - timedelta(days=days_past_monday)
    tuesday = monday + timedelta(days=1)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=monday):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 1 == len(calls)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=tuesday):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 1 == len(calls)


async def test_if_action_list_weekday(opp, calls):
    """Test for action with a list of weekdays."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": {"condition": "time", "weekday": ["mon", "tue"]},
                "action": {"service": "test.automation"},
            }
        },
    )

    days_past_monday = dt_util.now().weekday()
    monday = dt_util.now() - timedelta(days=days_past_monday)
    tuesday = monday + timedelta(days=1)
    wednesday = tuesday + timedelta(days=1)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=monday):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 1 == len(calls)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=tuesday):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 2 == len(calls)

    with patch("openpeerpower.helpers.condition.dt_util.now", return_value=wednesday):
        opp.bus.async_fire("test_event")
        await opp.async_block_till_done()

    assert 2 == len(calls)
