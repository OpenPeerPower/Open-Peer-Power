"""The tests for numeric state automation."""
from datetime import timedelta
from unittest.mock import patch

import pytest

import openpeerpower.components.automation as automation
from openpeerpower.core import Context
from openpeerpower.setup import async_setup_component
import openpeerpower.util.dt as dt_util

from tests.common import (
    assert_setup_component,
    async_fire_time_changed,
    async_mock_service,
    mock_component,
)
from tests.components.automation import common


@pytest.fixture
def calls(opp):
    """Track calls to a mock service."""
    return async_mock_service(opp, "test", "automation")


@pytest.fixture(autouse=True)
def setup_comp(opp):
    """Initialize components."""
    mock_component(opp, "group")


async def test_if_fires_on_entity_change_below(opp, calls):
    """Test the firing with changed entity."""
    context = Context()
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 9 is below 10
    opp.states.async_set("test.entity", 9, context=context)
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert calls[0].context.parent_id == context.id

    # Set above 12 so the automation will fire again
    opp.states.async_set("test.entity", 12)
    await common.async_turn_off(opp)
    await opp.async_block_till_done()
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_entity_change_over_to_below(opp, calls):
    """Test the firing with changed entity."""
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 9 is below 10
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_entities_change_over_to_below(opp, calls):
    """Test the firing with changed entities."""
    opp.states.async_set("test.entity_1", 11)
    opp.states.async_set("test.entity_2", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 9 is below 10
    opp.states.async_set("test.entity_1", 9)
    await opp.async_block_till_done()
    assert 1 == len(calls)
    opp.states.async_set("test.entity_2", 9)
    await opp.async_block_till_done()
    assert 2 == len(calls)


async def test_if_not_fires_on_entity_change_below_to_below(opp, calls):
    """Test the firing with changed entity."""
    context = Context()
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 9 is below 10 so this should fire
    opp.states.async_set("test.entity", 9, context=context)
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert calls[0].context.parent_id == context.id

    # already below so should not fire again
    opp.states.async_set("test.entity", 5)
    await opp.async_block_till_done()
    assert 1 == len(calls)

    # still below so should not fire again
    opp.states.async_set("test.entity", 3)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_below_fires_on_entity_change_to_equal(opp, calls):
    """Test the firing with changed entity."""
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 10 is not below 10 so this should not fire again
    opp.states.async_set("test.entity", 10)
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_fires_on_initial_entity_below(opp, calls):
    """Test the firing when starting with a match."""
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # Fire on first update even if initial state was already below
    opp.states.async_set("test.entity", 8)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_initial_entity_above(opp, calls):
    """Test the firing when starting with a match."""
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # Fire on first update even if initial state was already above
    opp.states.async_set("test.entity", 12)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_entity_change_above(opp, calls):
    """Test the firing with changed entity."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 11 is above 10
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_entity_change_below_to_above(opp, calls):
    """Test the firing with changed entity."""
    # set initial state
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 11 is above 10 and 9 is below
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_fires_on_entity_change_above_to_above(opp, calls):
    """Test the firing with changed entity."""
    # set initial state
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 12 is above 10 so this should fire
    opp.states.async_set("test.entity", 12)
    await opp.async_block_till_done()
    assert 1 == len(calls)

    # already above, should not fire again
    opp.states.async_set("test.entity", 15)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_above_fires_on_entity_change_to_equal(opp, calls):
    """Test the firing with changed entity."""
    # set initial state
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 10 is not above 10 so this should not fire again
    opp.states.async_set("test.entity", 10)
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_fires_on_entity_change_below_range(opp, calls):
    """Test the firing with changed entity."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                    "above": 5,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 9 is below 10
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_entity_change_below_above_range(opp, calls):
    """Test the firing with changed entity."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                    "above": 5,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 4 is below 5
    opp.states.async_set("test.entity", 4)
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_fires_on_entity_change_over_to_below_range(opp, calls):
    """Test the firing with changed entity."""
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                    "above": 5,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 9 is below 10
    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_entity_change_over_to_below_above_range(opp, calls):
    """Test the firing with changed entity."""
    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                    "above": 5,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    # 4 is below 5 so it should not fire
    opp.states.async_set("test.entity", 4)
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_not_fires_if_entity_not_match(opp, calls):
    """Test if not fired with non matching entity."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.another_entity",
                    "below": 100,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity", 11)
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_fires_on_entity_change_below_with_attribute(opp, calls):
    """Test attributes change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 9 is below 10
    opp.states.async_set("test.entity", 9, {"test_attribute": 11})
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_fires_on_entity_change_not_below_with_attribute(opp, calls):
    """Test attributes."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 11 is not below 10
    opp.states.async_set("test.entity", 11, {"test_attribute": 9})
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_fires_on_attribute_change_with_attribute_below(opp, calls):
    """Test attributes change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 9 is below 10
    opp.states.async_set("test.entity", "entity", {"test_attribute": 9})
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_fires_on_attribute_change_with_attribute_not_below(opp, calls):
    """Test attributes change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 11 is not below 10
    opp.states.async_set("test.entity", "entity", {"test_attribute": 11})
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_not_fires_on_entity_change_with_attribute_below(opp, calls):
    """Test attributes change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 11 is not below 10, entity state value should not be tested
    opp.states.async_set("test.entity", "9", {"test_attribute": 11})
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_not_fires_on_entity_change_with_not_attribute_below(opp, calls):
    """Test attributes change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 11 is not below 10, entity state value should not be tested
    opp.states.async_set("test.entity", "entity")
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_fires_on_attr_change_with_attribute_below_and_multiple_attr(opp, calls):
    """Test attributes change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 9 is not below 10
    opp.states.async_set(
        "test.entity", "entity", {"test_attribute": 9, "not_test_attribute": 11}
    )
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_template_list(opp, calls):
    """Test template list."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute[2] }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 3 is below 10
    opp.states.async_set("test.entity", "entity", {"test_attribute": [11, 15, 3]})
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_template_string(opp, calls):
    """Test template string."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute | multiply(10) }}",
                    "below": 10,
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.%s }}"
                        % "}} - {{ trigger.".join(
                            (
                                "platform",
                                "entity_id",
                                "below",
                                "above",
                                "from_state.state",
                                "to_state.state",
                            )
                        )
                    },
                },
            }
        },
    )
    opp.states.async_set("test.entity", "test state 1", {"test_attribute": "1.2"})
    await opp.async_block_till_done()
    opp.states.async_set("test.entity", "test state 2", {"test_attribute": "0.9"})
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert (
        "numeric_state - test.entity - 10.0 - None - test state 1 - "
        "test state 2" == calls[0].data["some"]
    )


async def test_not_fires_on_attr_change_with_attr_not_below_multiple_attr(opp, calls):
    """Test if not fired changed attributes."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "value_template": "{{ state.attributes.test_attribute }}",
                    "below": 10,
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    # 11 is not below 10
    opp.states.async_set(
        "test.entity", "entity", {"test_attribute": 11, "not_test_attribute": 9}
    )
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_action(opp, calls):
    """Test if action."""
    entity_id = "domain.test_entity"
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "event", "event_type": "test_event"},
                "condition": {
                    "condition": "numeric_state",
                    "entity_id": entity_id,
                    "above": 8,
                    "below": 12,
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set(entity_id, 10)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert 1 == len(calls)

    opp.states.async_set(entity_id, 8)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert 1 == len(calls)

    opp.states.async_set(entity_id, 9)
    opp.bus.async_fire("test_event")
    await opp.async_block_till_done()

    assert 2 == len(calls)


async def test_if_fails_setup_bad_for(opp, calls):
    """Test for setup failure for bad for."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": {"invalid": 5},
                },
                "action": {"service": "openpeerpower.turn_on"},
            }
        },
    )

    with patch.object(automation.numeric_state, "_LOGGER") as mock_logger:
        opp.states.async_set("test.entity", 9)
        await opp.async_block_till_done()
        assert mock_logger.error.called


async def test_if_fails_setup_for_without_above_below(opp, calls):
    """Test for setup failures for missing above or below."""
    with assert_setup_component(0, automation.DOMAIN):
        assert await async_setup_component(
            opp,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "trigger": {
                        "platform": "numeric_state",
                        "entity_id": "test.entity",
                        "for": {"seconds": 5},
                    },
                    "action": {"service": "openpeerpower.turn_on"},
                }
            },
        )


async def test_if_not_fires_on_entity_change_with_for(opp, calls):
    """Test for not firing on entity change with for."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    opp.states.async_set("test.entity", 15)
    await opp.async_block_till_done()
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_if_not_fires_on_entities_change_with_for_after_stop(opp, calls):
    """Test for not firing on entities change with for after stop."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity_1", 9)
    opp.states.async_set("test.entity_2", 9)
    await opp.async_block_till_done()
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 2 == len(calls)

    opp.states.async_set("test.entity_1", 15)
    opp.states.async_set("test.entity_2", 15)
    await opp.async_block_till_done()
    opp.states.async_set("test.entity_1", 9)
    opp.states.async_set("test.entity_2", 9)
    await opp.async_block_till_done()
    await common.async_turn_off(opp)
    await opp.async_block_till_done()

    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 2 == len(calls)


async def test_if_fires_on_entity_change_with_for_attribute_change(opp, calls):
    """Test for firing on entity change with for and attribute change."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    utcnow = dt_util.utcnow()
    with patch("openpeerpower.core.dt_util.utcnow") as mock_utcnow:
        mock_utcnow.return_value = utcnow
        opp.states.async_set("test.entity", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=4)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity", 9, attributes={"mock_attr": "attr_change"})
        await opp.async_block_till_done()
        assert 0 == len(calls)
        mock_utcnow.return_value += timedelta(seconds=4)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 1 == len(calls)


async def test_if_fires_on_entity_change_with_for(opp, calls):
    """Test for firing on entity change with for."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": 5},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_wait_template_with_trigger(opp, calls):
    """Test using wait template with 'trigger.entity_id'."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 10,
                },
                "action": [
                    {"wait_template": "{{ states(trigger.entity_id) | int < 10 }}"},
                    {
                        "service": "test.automation",
                        "data_template": {
                            "some": "{{ trigger.%s }}"
                            % "}} - {{ trigger.".join(
                                ("platform", "entity_id", "to_state.state")
                            )
                        },
                    },
                ],
            }
        },
    )

    await opp.async_block_till_done()

    opp.states.async_set("test.entity", "12")
    await opp.async_block_till_done()
    opp.states.async_set("test.entity", "8")
    await opp.async_block_till_done()
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert "numeric_state - test.entity - 12" == calls[0].data["some"]


async def test_if_fires_on_entities_change_no_overlap(opp, calls):
    """Test for firing on entities change with no overlap."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": 5},
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {"some": "{{ trigger.entity_id }}"},
                },
            }
        },
    )
    await opp.async_block_till_done()

    utcnow = dt_util.utcnow()
    with patch("openpeerpower.core.dt_util.utcnow") as mock_utcnow:
        mock_utcnow.return_value = utcnow
        opp.states.async_set("test.entity_1", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=10)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 1 == len(calls)
        assert "test.entity_1" == calls[0].data["some"]

        opp.states.async_set("test.entity_2", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=10)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 2 == len(calls)
        assert "test.entity_2" == calls[1].data["some"]


async def test_if_fires_on_entities_change_overlap(opp, calls):
    """Test for firing on entities change with overlap."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": 5},
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {"some": "{{ trigger.entity_id }}"},
                },
            }
        },
    )
    await opp.async_block_till_done()

    utcnow = dt_util.utcnow()
    with patch("openpeerpower.core.dt_util.utcnow") as mock_utcnow:
        mock_utcnow.return_value = utcnow
        opp.states.async_set("test.entity_1", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=1)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity_2", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=1)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity_2", 15)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=1)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity_2", 9)
        await opp.async_block_till_done()
        assert 0 == len(calls)
        mock_utcnow.return_value += timedelta(seconds=3)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 1 == len(calls)
        assert "test.entity_1" == calls[0].data["some"]

        mock_utcnow.return_value += timedelta(seconds=3)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 2 == len(calls)
        assert "test.entity_2" == calls[1].data["some"]


async def test_if_fires_on_change_with_for_template_1(opp, calls):
    """Test for firing on  change with for template."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": {"seconds": "{{ 5 }}"},
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 0 == len(calls)
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_change_with_for_template_2(opp, calls):
    """Test for firing on  change with for template."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": "{{ 5 }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 0 == len(calls)
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_change_with_for_template_3(opp, calls):
    """Test for firing on  change with for template."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": "00:00:{{ 5 }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    opp.states.async_set("test.entity", 9)
    await opp.async_block_till_done()
    assert 0 == len(calls)
    async_fire_time_changed(opp, dt_util.utcnow() + timedelta(seconds=10))
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_invalid_for_template(opp, calls):
    """Test for invalid for template."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": "test.entity",
                    "above": 8,
                    "below": 12,
                    "for": "{{ five }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    with patch.object(automation.numeric_state, "_LOGGER") as mock_logger:
        opp.states.async_set("test.entity", 9)
        await opp.async_block_till_done()
        assert mock_logger.error.called


async def test_if_fires_on_entities_change_overlap_for_template(opp, calls):
    """Test for firing on entities change with overlap and for template."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "numeric_state",
                    "entity_id": ["test.entity_1", "test.entity_2"],
                    "above": 8,
                    "below": 12,
                    "for": '{{ 5 if trigger.entity_id == "test.entity_1"'
                    "   else 10 }}",
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.entity_id }} - {{ trigger.for }}"
                    },
                },
            }
        },
    )
    await opp.async_block_till_done()

    utcnow = dt_util.utcnow()
    with patch("openpeerpower.util.dt.utcnow") as mock_utcnow:
        mock_utcnow.return_value = utcnow
        opp.states.async_set("test.entity_1", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=1)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity_2", 9)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=1)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity_2", 15)
        await opp.async_block_till_done()
        mock_utcnow.return_value += timedelta(seconds=1)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        opp.states.async_set("test.entity_2", 9)
        await opp.async_block_till_done()
        assert 0 == len(calls)
        mock_utcnow.return_value += timedelta(seconds=3)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 1 == len(calls)
        assert "test.entity_1 - 0:00:05" == calls[0].data["some"]

        mock_utcnow.return_value += timedelta(seconds=3)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 1 == len(calls)
        mock_utcnow.return_value += timedelta(seconds=5)
        async_fire_time_changed(opp, mock_utcnow.return_value)
        await opp.async_block_till_done()
        assert 2 == len(calls)
        assert "test.entity_2 - 0:00:10" == calls[1].data["some"]
