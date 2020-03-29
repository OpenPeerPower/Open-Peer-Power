"""The test for zha device automation actions."""
from unittest.mock import patch

import pytest
import zigpy.zcl.clusters.general as general
import zigpy.zcl.clusters.security as security
import zigpy.zcl.foundation as zcl_f

import openpeerpower.components.automation as automation
from openpeerpower.components.device_automation import (
    _async_get_device_automations as async_get_device_automations,
)
from openpeerpower.components.zha import DOMAIN
from openpeerpower.components.zha.core.const import CHANNEL_EVENT_RELAY
from openpeerpower.helpers.device_registry import async_get_registry
from openpeerpower.setup import async_setup_component

from tests.common import async_mock_service, mock_coro

SHORT_PRESS = "remote_button_short_press"
COMMAND = "command"
COMMAND_SINGLE = "single"


@pytest.fixture
async def device_ias(opp, zigpy_device_mock, zha_device_joined_restored):
    """IAS device fixture."""

    clusters = [general.Basic, security.IasZone, security.IasWd]
    zigpy_device = zigpy_device_mock(
        {
            1: {
                "in_clusters": [c.cluster_id for c in clusters],
                "out_clusters": [general.OnOff.cluster_id],
                "device_type": 0,
            }
        },
    )

    zha_device = await zha_device_joined_restored(zigpy_device)
    zha_device.update_available(True)
    await opp.async_block_till_done()
    return zigpy_device, zha_device


async def test_get_actions(opp, device_ias):
    """Test we get the expected actions from a zha device."""

    ieee_address = str(device_ias[0].ieee)

    op_device_registry = await async_get_registry(opp)
    reg_device = op_device_registry.async_get_device({(DOMAIN, ieee_address)}, set())

    actions = await async_get_device_automations(opp, "action", reg_device.id)

    expected_actions = [
        {"domain": DOMAIN, "type": "squawk", "device_id": reg_device.id},
        {"domain": DOMAIN, "type": "warn", "device_id": reg_device.id},
    ]

    assert actions == expected_actions


async def test_action(opp, device_ias):
    """Test for executing a zha device action."""
    zigpy_device, zha_device = device_ias

    zigpy_device.device_automation_triggers = {
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE}
    }

    ieee_address = str(zha_device.ieee)

    op_device_registry = await async_get_registry(opp)
    reg_device = op_device_registry.async_get_device({(DOMAIN, ieee_address)}, set())

    with patch(
        "zigpy.zcl.Cluster.request",
        return_value=mock_coro([0x00, zcl_f.Status.SUCCESS]),
    ):
        assert await async_setup_component(
            opp,
            automation.DOMAIN,
            {
                automation.DOMAIN: [
                    {
                        "trigger": {
                            "device_id": reg_device.id,
                            "domain": "zha",
                            "platform": "device",
                            "type": SHORT_PRESS,
                            "subtype": SHORT_PRESS,
                        },
                        "action": {
                            "domain": DOMAIN,
                            "device_id": reg_device.id,
                            "type": "warn",
                        },
                    }
                ]
            },
        )

        await opp.async_block_till_done()
        calls = async_mock_service(opp, DOMAIN, "warning_device_warn")

        channel = {ch.name: ch for ch in zha_device.all_channels}[CHANNEL_EVENT_RELAY]
        channel.zha_send_event(channel.cluster, COMMAND_SINGLE, [])
        await opp.async_block_till_done()

        assert len(calls) == 1
        assert calls[0].domain == DOMAIN
        assert calls[0].service == "warning_device_warn"
        assert calls[0].data["ieee"] == ieee_address
