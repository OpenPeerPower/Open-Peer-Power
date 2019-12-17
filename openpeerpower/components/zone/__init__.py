"""Support for the definition of zones."""
import logging

import voluptuous as vol

import openpeerpower.helpers.config_validation as cv
from openpeerpower.const import (
    CONF_NAME, CONF_LATITUDE, CONF_LONGITUDE, CONF_ICON, CONF_RADIUS)
from openpeerpower.helpers import config_per_platform
from openpeerpower.helpers.entity import async_generate_entity_id
from openpeerpower.util import slugify

from .config_flow import configured_zones
from .const import CONF_PASSIVE, DOMAIN, HOME_ZONE
from .zone import Zone

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Unnamed zone'
DEFAULT_PASSIVE = False
DEFAULT_RADIUS = 100

ENTITY_ID_FORMAT = 'zone.{}'
ENTITY_ID_HOME = ENTITY_ID_FORMAT.format(HOME_ZONE)

ICON_HOME = 'mdi:home'
ICON_IMPORT = 'mdi:import'

# The config that zone accepts is the same as if it has platforms.
PLATFORM_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_LATITUDE): cv.latitude,
    vol.Required(CONF_LONGITUDE): cv.longitude,
    vol.Optional(CONF_RADIUS, default=DEFAULT_RADIUS): vol.Coerce(float),
    vol.Optional(CONF_PASSIVE, default=DEFAULT_PASSIVE): cv.boolean,
    vol.Optional(CONF_ICON): cv.icon,
}, extra=vol.ALLOW_EXTRA)


async def async_setup(opp, config):
    """Set up configured zones as well as open peer power zone if necessary."""
    opp.data[DOMAIN] = {}
    entities = set()
    zone_entries = configured_zones(opp)
    for _, entry in config_per_platform(config, DOMAIN):
        if slugify(entry[CONF_NAME]) not in zone_entries:
            zone = Zone(opp, entry[CONF_NAME], entry[CONF_LATITUDE],
                        entry[CONF_LONGITUDE], entry.get(CONF_RADIUS),
                        entry.get(CONF_ICON), entry.get(CONF_PASSIVE))
            zone.entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, entry[CONF_NAME], entities)
            opp.async_create_task(zone.async_update_op_state())
            entities.add(zone.entity_id)

    if ENTITY_ID_HOME not in entities and HOME_ZONE not in zone_entries:
        zone = Zone(opp, opp.config.location_name,
                    opp.config.latitude, opp.config.longitude,
                    DEFAULT_RADIUS, ICON_HOME, False)
        zone.entity_id = ENTITY_ID_HOME
        opp.async_create_task(zone.async_update_op_state())

    return True


async def async_setup_entry(opp, config_entry):
    """Set up zone as config entry."""
    entry = config_entry.data
    name = entry[CONF_NAME]
    zone = Zone(opp, name, entry[CONF_LATITUDE], entry[CONF_LONGITUDE],
                entry.get(CONF_RADIUS, DEFAULT_RADIUS), entry.get(CONF_ICON),
                entry.get(CONF_PASSIVE, DEFAULT_PASSIVE))
    zone.entity_id = async_generate_entity_id(
        ENTITY_ID_FORMAT, name, None, opp)
    opp.async_create_task(zone.async_update_op_state())
    opp.data[DOMAIN][slugify(name)] = zone
    return True


async def async_unload_entry(opp, config_entry):
    """Unload a config entry."""
    zones = opp.data[DOMAIN]
    name = slugify(config_entry.data[CONF_NAME])
    zone = zones.pop(name)
    await zone.async_remove()
    return True
