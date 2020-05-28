"""Provides device trigger for lights."""
from typing import List

import voluptuous as vol

from openpeerpower.components.automation import AutomationActionType
from openpeerpower.components.device_automation import toggle_entity
from openpeerpower.const import CONF_DOMAIN
from openpeerpower.core import CALLBACK_TYPE, OpenPeerPower
from openpeerpower.helpers.typing import ConfigType

from . import DOMAIN

TRIGGER_SCHEMA = toggle_entity.TRIGGER_SCHEMA.extend(
    {vol.Required(CONF_DOMAIN): DOMAIN}
)


async def async_attach_trigger(
    opp: OpenPeerPower,
    config: ConfigType,
    action: AutomationActionType,
    automation_info: dict,
) -> CALLBACK_TYPE:
    """Listen for state changes based on configuration."""
    return await toggle_entity.async_attach_trigger(
        opp, config, action, automation_info
    )


async def async_get_triggers(opp: OpenPeerPower, device_id: str) -> List[dict]:
    """List device triggers."""
    return await toggle_entity.async_get_triggers(opp, device_id, DOMAIN)


async def async_get_trigger_capabilities(opp: OpenPeerPower, config: dict) -> dict:
    """List trigger capabilities."""
    return await toggle_entity.async_get_trigger_capabilities(opp, config)
