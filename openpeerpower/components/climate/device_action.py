"""Provides device automations for Climate."""
from typing import List, Optional

import voluptuous as vol

from openpeerpower.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
)
from openpeerpower.core import Context, OpenPeerPower
from openpeerpower.helpers import entity_registry
import openpeerpower.helpers.config_validation as cv

from . import DOMAIN, const

ACTION_TYPES = {"set_hvac_mode", "set_preset_mode"}

SET_HVAC_MODE_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): "set_hvac_mode",
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(DOMAIN),
        vol.Required(const.ATTR_HVAC_MODE): vol.In(const.HVAC_MODES),
    }
)

SET_PRESET_MODE_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): "set_preset_mode",
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(DOMAIN),
        vol.Required(const.ATTR_PRESET_MODE): str,
    }
)

ACTION_SCHEMA = vol.Any(SET_HVAC_MODE_SCHEMA, SET_PRESET_MODE_SCHEMA)


async def async_get_actions(opp: OpenPeerPower, device_id: str) -> List[dict]:
    """List device actions for Climate devices."""
    registry = await entity_registry.async_get_registry(opp)
    actions = []

    # Get all the integrations entities for this device
    for entry in entity_registry.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        state = opp.states.get(entry.entity_id)

        # We need a state or else we can't populate the HVAC and preset modes.
        if state is None:
            continue

        actions.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "set_hvac_mode",
            }
        )
        if state.attributes["supported_features"] & const.SUPPORT_PRESET_MODE:
            actions.append(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DOMAIN: DOMAIN,
                    CONF_ENTITY_ID: entry.entity_id,
                    CONF_TYPE: "set_preset_mode",
                }
            )

    return actions


async def async_call_action_from_config(
    opp: OpenPeerPower, config: dict, variables: dict, context: Optional[Context]
) -> None:
    """Execute a device action."""
    config = ACTION_SCHEMA(config)

    service_data = {ATTR_ENTITY_ID: config[CONF_ENTITY_ID]}

    if config[CONF_TYPE] == "set_hvac_mode":
        service = const.SERVICE_SET_HVAC_MODE
        service_data[const.ATTR_HVAC_MODE] = config[const.ATTR_HVAC_MODE]
    elif config[CONF_TYPE] == "set_preset_mode":
        service = const.SERVICE_SET_PRESET_MODE
        service_data[const.ATTR_PRESET_MODE] = config[const.ATTR_PRESET_MODE]

    await opp.services.async_call(
        DOMAIN, service, service_data, blocking=True, context=context
    )


async def async_get_action_capabilities(opp, config):
    """List action capabilities."""
    state = opp.states.get(config[CONF_ENTITY_ID])
    action_type = config[CONF_TYPE]

    fields = {}

    if action_type == "set_hvac_mode":
        hvac_modes = state.attributes[const.ATTR_HVAC_MODES] if state else []
        fields[vol.Required(const.ATTR_HVAC_MODE)] = vol.In(hvac_modes)
    elif action_type == "set_preset_mode":
        if state:
            preset_modes = state.attributes.get(const.ATTR_PRESET_MODES, [])
        else:
            preset_modes = []
        fields[vol.Required(const.ATTR_PRESET_MODE)] = vol.In(preset_modes)

    return {"extra_fields": vol.Schema(fields)}
