"""Provides device conditions for switches."""
from typing import Dict, List

import voluptuous as vol

from openpeerpower.components.device_automation import toggle_entity
from openpeerpower.const import CONF_DOMAIN
from openpeerpower.core import OpenPeerPower, callback
from openpeerpower.helpers.condition import ConditionCheckerType
from openpeerpower.helpers.typing import ConfigType

from . import DOMAIN

CONDITION_SCHEMA = toggle_entity.CONDITION_SCHEMA.extend(
    {vol.Required(CONF_DOMAIN): DOMAIN}
)


@callback
def async_condition_from_config(
    config: ConfigType, config_validation: bool
) -> ConditionCheckerType:
    """Evaluate state based on configuration."""
    if config_validation:
        config = CONDITION_SCHEMA(config)
    return toggle_entity.async_condition_from_config(config)


async def async_get_conditions(
    opp: OpenPeerPower, device_id: str
) -> List[Dict[str, str]]:
    """List device conditions."""
    return await toggle_entity.async_get_conditions(opp, device_id, DOMAIN)


async def async_get_condition_capabilities(opp: OpenPeerPower, config: dict) -> dict:
    """List condition capabilities."""
    return await toggle_entity.async_get_condition_capabilities(opp, config)
