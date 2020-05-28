"""
This package contains components that can be plugged into Open Peer Power.

Component design guidelines:
- Each component defines a constant DOMAIN that is equal to its filename.
- Each component that tracks states should create state entity names in the
  format "<DOMAIN>.<OBJECT_ID>".
- Each component should publish services only under its own domain.
"""
import logging

from openpeerpower.core import split_entity_id

# mypy: allow-untyped-defs

_LOGGER = logging.getLogger(__name__)


def is_on(opp, entity_id=None):
    """Load up the module to call the is_on method.

    If there is no entity id given we will check all.
    """
    if entity_id:
        entity_ids = opp.components.group.expand_entity_ids([entity_id])
    else:
        entity_ids = opp.states.entity_ids()

    for ent_id in entity_ids:
        domain = split_entity_id(ent_id)[0]

        try:
            component = getattr(opp.components, domain)

        except ImportError:
            _LOGGER.error("Failed to call %s.is_on: component not found", domain)
            continue

        if not hasattr(component, "is_on"):
            _LOGGER.warning("Integration %s has no is_on method.", domain)
            continue

        if component.is_on(ent_id):
            return True

    return False
