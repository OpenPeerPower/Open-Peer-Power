"""Provides device actions for ZHA devices."""
from typing import List

import voluptuous as vol

from openpeerpower.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_TYPE
from openpeerpower.core import Context, OpenPeerPower
from openpeerpower.helpers import config_validation as cv
from openpeerpower.helpers.typing import ConfigType, TemplateVarsType

from . import DOMAIN
from .api import SERVICE_WARNING_DEVICE_SQUAWK, SERVICE_WARNING_DEVICE_WARN
from .core.const import CHANNEL_IAS_WD
from .core.helpers import async_get_zha_device

ACTION_SQUAWK = "squawk"
ACTION_WARN = "warn"
ATTR_DATA = "data"
ATTR_IEEE = "ieee"
CONF_ZHA_ACTION_TYPE = "zha_action_type"
ZHA_ACTION_TYPE_SERVICE_CALL = "service_call"

ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {vol.Required(CONF_DOMAIN): DOMAIN, vol.Required(CONF_TYPE): str}
)

DEVICE_ACTIONS = {
    CHANNEL_IAS_WD: [
        {CONF_TYPE: ACTION_SQUAWK, CONF_DOMAIN: DOMAIN},
        {CONF_TYPE: ACTION_WARN, CONF_DOMAIN: DOMAIN},
    ]
}

DEVICE_ACTION_TYPES = {
    ACTION_SQUAWK: ZHA_ACTION_TYPE_SERVICE_CALL,
    ACTION_WARN: ZHA_ACTION_TYPE_SERVICE_CALL,
}

SERVICE_NAMES = {
    ACTION_SQUAWK: SERVICE_WARNING_DEVICE_SQUAWK,
    ACTION_WARN: SERVICE_WARNING_DEVICE_WARN,
}


async def async_call_action_from_config(
    opp: OpenPeerPower,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context,
) -> None:
    """Perform an action based on configuration."""
    await ZHA_ACTION_TYPES[DEVICE_ACTION_TYPES[config[CONF_TYPE]]](
        opp, config, variables, context
    )


async def async_get_actions(opp: OpenPeerPower, device_id: str) -> List[dict]:
    """List device actions."""
    zha_device = await async_get_zha_device(opp, device_id)
    actions = [
        action
        for channel in DEVICE_ACTIONS
        for action in DEVICE_ACTIONS[channel]
        if channel in zha_device.cluster_channels
    ]
    for action in actions:
        action[CONF_DEVICE_ID] = device_id
    return actions


async def _execute_service_based_action(
    opp: OpenPeerPower,
    config: ACTION_SCHEMA,
    variables: TemplateVarsType,
    context: Context,
) -> None:
    action_type = config[CONF_TYPE]
    service_name = SERVICE_NAMES[action_type]
    zha_device = await async_get_zha_device(opp, config[CONF_DEVICE_ID])

    service_data = {ATTR_IEEE: str(zha_device.ieee)}

    await opp.services.async_call(
        DOMAIN, service_name, service_data, blocking=True, context=context
    )


ZHA_ACTION_TYPES = {ZHA_ACTION_TYPE_SERVICE_CALL: _execute_service_based_action}
