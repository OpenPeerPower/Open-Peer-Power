"""Collection of helper methods.

All containing methods are legacy helpers that should not be used by new
components. Instead call the service directly.
"""
from openpeerpower.components.scene import DOMAIN
from openpeerpower.const import ATTR_ENTITY_ID, ENTITY_MATCH_ALL, SERVICE_TURN_ON
from openpeerpower.loader import bind_opp


@bind_opp
def activate(opp, entity_id=ENTITY_MATCH_ALL):
    """Activate a scene."""
    data = {}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    opp.services.call(DOMAIN, SERVICE_TURN_ON, data)
