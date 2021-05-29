"""Offer zone automation rules."""
import voluptuous as vol

from openpeerpower.const import (
    CONF_ENTITY_ID,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_ZONE,
    MATCH_ALL,
)
from openpeerpower.core import callback
from openpeerpower.helpers import condition, config_validation as cv, location
from openpeerpower.helpers.event import async_track_state_change

# mypy: allow-untyped-defs, no-check-untyped-defs

EVENT_ENTER = "enter"
EVENT_LEAVE = "leave"
DEFAULT_EVENT = EVENT_ENTER

TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): "zone",
        vol.Required(CONF_ENTITY_ID): cv.entity_ids,
        vol.Required(CONF_ZONE): cv.entity_id,
        vol.Required(CONF_EVENT, default=DEFAULT_EVENT): vol.Any(
            EVENT_ENTER, EVENT_LEAVE
        ),
    }
)


async def async_attach_trigger(opp, config, action, automation_info):
    """Listen for state changes based on configuration."""
    entity_id = config.get(CONF_ENTITY_ID)
    zone_entity_id = config.get(CONF_ZONE)
    event = config.get(CONF_EVENT)

    @callback
    def zone_automation_listener(entity, from_s, to_s):
        """Listen for state changes and calls action."""
        if (
            from_s
            and not location.has_location(from_s)
            or not location.has_location(to_s)
        ):
            return

        zone_state = opp.states.get(zone_entity_id)
        if from_s:
            from_match = condition.zone(opp, zone_state, from_s)
        else:
            from_match = False
        to_match = condition.zone(opp, zone_state, to_s)

        # pylint: disable=too-many-boolean-expressions
        if (
            event == EVENT_ENTER
            and not from_match
            and to_match
            or event == EVENT_LEAVE
            and from_match
            and not to_match
        ):
            opp.async_run_job(
                action(
                    {
                        "trigger": {
                            "platform": "zone",
                            "entity_id": entity,
                            "from_state": from_s,
                            "to_state": to_s,
                            "zone": zone_state,
                            "event": event,
                        }
                    },
                    context=to_s.context,
                )
            )

    return async_track_state_change(
        opp, entity_id, zone_automation_listener, MATCH_ALL, MATCH_ALL
    )