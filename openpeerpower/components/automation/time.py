"""Offer time listening automation rules."""
import logging

import voluptuous as vol

from openpeerpower.const import CONF_AT, CONF_PLATFORM
from openpeerpower.core import callback
from openpeerpower.helpers import config_validation as cv
from openpeerpower.helpers.event import async_track_time_change

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = vol.Schema(
    {vol.Required(CONF_PLATFORM): "time", vol.Required(CONF_AT): cv.time}
)


async def async_attach_trigger(opp, config, action, automation_info):
    """Listen for state changes based on configuration."""
    at_time = config.get(CONF_AT)
    hours, minutes, seconds = at_time.hour, at_time.minute, at_time.second

    @callback
    def time_automation_listener(now):
        """Listen for time changes and calls action."""
        opp.async_run_job(action, {"trigger": {"platform": "time", "now": now}})

    return async_track_time_change(
        opp, time_automation_listener, hour=hours, minute=minutes, second=seconds
    )
