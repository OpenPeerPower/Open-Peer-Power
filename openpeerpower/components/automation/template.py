"""Offer template automation rules."""
import logging

import voluptuous as vol

from openpeerpower.core import callback
from openpeerpower.const import CONF_VALUE_TEMPLATE, CONF_PLATFORM
from openpeerpower.helpers.event import async_track_template
import openpeerpower.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

TRIGGER_SCHEMA = IF_ACTION_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): 'template',
    vol.Required(CONF_VALUE_TEMPLATE): cv.template,
})


async def async_trigger(opp, config, action, automation_info):
    """Listen for state changes based on configuration."""
    value_template = config.get(CONF_VALUE_TEMPLATE)
    value_template.opp = opp

    @callback
    def template_listener(entity_id, from_s, to_s):
        """Listen for state changes and calls action."""
        opp.async_run_job(action({
            'trigger': {
                'platform': 'template',
                'entity_id': entity_id,
                'from_state': from_s,
                'to_state': to_s,
            },
        }, context=(to_s.context if to_s else None)))

    return async_track_template(opp, value_template, template_listener)
