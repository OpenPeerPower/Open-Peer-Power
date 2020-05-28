"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""
from openpeerpower.components.automation import (
    CONF_SKIP_CONDITION,
    DOMAIN,
    SERVICE_TRIGGER,
)
from openpeerpower.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_RELOAD,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from openpeerpower.loader import bind_opp


@bind_opp
async def async_turn_on(opp, entity_id=ENTITY_MATCH_ALL):
    """Turn on specified automation or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await opp.services.async_call(DOMAIN, SERVICE_TURN_ON, data)


@bind_opp
async def async_turn_off(opp, entity_id=ENTITY_MATCH_ALL):
    """Turn off specified automation or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await opp.services.async_call(DOMAIN, SERVICE_TURN_OFF, data)


@bind_opp
async def async_toggle(opp, entity_id=ENTITY_MATCH_ALL):
    """Toggle specified automation or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    await opp.services.async_call(DOMAIN, SERVICE_TOGGLE, data)


@bind_opp
async def async_trigger(opp, entity_id=ENTITY_MATCH_ALL, skip_condition=True):
    """Trigger specified automation or all."""
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    data[CONF_SKIP_CONDITION] = skip_condition
    await opp.services.async_call(DOMAIN, SERVICE_TRIGGER, data)


@bind_opp
async def async_reload(opp, context=None):
    """Reload the automation from config."""
    await opp.services.async_call(
        DOMAIN, SERVICE_RELOAD, blocking=True, context=context
    )
