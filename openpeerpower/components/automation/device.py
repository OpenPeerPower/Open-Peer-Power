"""Offer device oriented automation."""
import voluptuous as vol

from openpeerpower.components.device_automation import (
    TRIGGER_BASE_SCHEMA,
    async_get_device_automation_platform,
)
from openpeerpower.const import CONF_DOMAIN

# mypy: allow-untyped-defs, no-check-untyped-defs

TRIGGER_SCHEMA = TRIGGER_BASE_SCHEMA.extend({}, extra=vol.ALLOW_EXTRA)


async def async_validate_trigger_config(opp, config):
    """Validate config."""
    platform = await async_get_device_automation_platform(
        opp, config[CONF_DOMAIN], "trigger"
    )
    if hasattr(platform, "async_validate_trigger_config"):
        return await getattr(platform, "async_validate_trigger_config")(opp, config)

    return platform.TRIGGER_SCHEMA(config)


async def async_attach_trigger(opp, config, action, automation_info):
    """Listen for trigger."""
    platform = await async_get_device_automation_platform(
        opp, config[CONF_DOMAIN], "trigger"
    )
    return await platform.async_attach_trigger(opp, config, action, automation_info)
