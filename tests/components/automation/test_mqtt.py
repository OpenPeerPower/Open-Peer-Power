"""The tests for the MQTT automation."""
from unittest import mock

import pytest

import openpeerpower.components.automation as automation
from openpeerpower.setup import async_setup_component

from tests.common import (
    async_fire_mqtt_message,
    async_mock_mqtt_component,
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
    opp.loop.run_until_complete(async_mock_mqtt_component(opp))


async def test_if_fires_on_topic_match(opp, calls):
    """Test if message is fired on topic match."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "mqtt", "topic": "test-topic"},
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.platform }} - {{ trigger.topic }}"
                        " - {{ trigger.payload }} - "
                        "{{ trigger.payload_json.hello }}"
                    },
                },
            }
        },
    )

    async_fire_mqtt_message(opp, "test-topic", '{ "hello": "world" }')
    await opp.async_block_till_done()
    assert 1 == len(calls)
    assert 'mqtt - test-topic - { "hello": "world" } - world' == calls[0].data["some"]

    await common.async_turn_off(opp)
    await opp.async_block_till_done()
    async_fire_mqtt_message(opp, "test-topic", "test_payload")
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_fires_on_topic_and_payload_match(opp, calls):
    """Test if message is fired on topic and payload match."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic",
                    "payload": "hello",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(opp, "test-topic", "hello")
    await opp.async_block_till_done()
    assert 1 == len(calls)


async def test_if_not_fires_on_topic_but_no_payload_match(opp, calls):
    """Test if message is not fired on topic but no payload."""
    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic",
                    "payload": "hello",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(opp, "test-topic", "no-hello")
    await opp.async_block_till_done()
    assert 0 == len(calls)


async def test_encoding_default(opp, calls):
    """Test default encoding."""
    mock_mqtt = await async_mock_mqtt_component(opp)

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "mqtt", "topic": "test-topic"},
                "action": {"service": "test.automation"},
            }
        },
    )

    mock_mqtt.async_subscribe.assert_called_once_with(
        "test-topic", mock.ANY, 0, "utf-8"
    )


async def test_encoding_custom(opp, calls):
    """Test default encoding."""
    mock_mqtt = await async_mock_mqtt_component(opp)

    assert await async_setup_component(
        opp,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "mqtt", "topic": "test-topic", "encoding": ""},
                "action": {"service": "test.automation"},
            }
        },
    )

    mock_mqtt.async_subscribe.assert_called_once_with("test-topic", mock.ANY, 0, None)
