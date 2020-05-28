"""Provides device actions for switches."""
from typing import List

import voluptuous as vol

from openpeerpower.components.device_automation import toggle_entity
from openpeerpower.const import CONF_DOMAIN
from openpeerpower.core import Context, OpenPeerPower
from openpeerpower.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN

ACTION_SCHEMA = toggle_entity.ACTION_SCHEMA.extend({vol.Required(CONF_DOMAIN): DOMAIN})


async def async_call_action_from_config(
    opp: OpenPeerPower,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context,
) -> None:
    """Change state based on configuration."""
    await toggle_entity.async_call_action_from_config(
        opp, config, variables, context, DOMAIN
    )


async def async_get_actions(opp: OpenPeerPower, device_id: str) -> List[dict]:
    """List device actions."""
    return await toggle_entity.async_get_actions(opp, device_id, DOMAIN)
