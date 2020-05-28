"""Offer sun based automation rules."""
from datetime import timedelta
import logging

import voluptuous as vol

from openpeerpower.const import (
    CONF_EVENT,
    CONF_OFFSET,
    CONF_PLATFORM,
    SUN_EVENT_SUNRISE,
)
from openpeerpower.core import callback
import openpeerpower.helpers.config_validation as cv
from openpeerpower.helpers.event import async_track_sunrise, async_track_sunset

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): "sun",
        vol.Required(CONF_EVENT): cv.sun_event,
        vol.Required(CONF_OFFSET, default=timedelta(0)): cv.time_period,
    }
)


async def async_attach_trigger(opp, config, action, automation_info):
    """Listen for events based on configuration."""
    event = config.get(CONF_EVENT)
    offset = config.get(CONF_OFFSET)

    @callback
    def call_action():
        """Call action with right context."""
        opp.async_run_job(
            action, {"trigger": {"platform": "sun", "event": event, "offset": offset}}
        )

    if event == SUN_EVENT_SUNRISE:
        return async_track_sunrise(opp, call_action, offset)
    return async_track_sunset(opp, call_action, offset)
