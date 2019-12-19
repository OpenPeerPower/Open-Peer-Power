"""Support for Geolocation."""
from datetime import timedelta
import logging
from typing import Optional

from openpeerpower.const import ATTR_LATITUDE, ATTR_LONGITUDE
from openpeerpower.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from openpeerpower.helpers.entity import Entity
from openpeerpower.helpers.entity_component import EntityComponent

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

ATTR_DISTANCE = "distance"
ATTR_SOURCE = "source"

DOMAIN = "geo_location"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup(opp, config):
    """Set up the Geolocation component."""
    component = opp.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, opp, SCAN_INTERVAL
    )
    await component.async_setup(config)
    return True


async def async_setup_entry(opp, entry):
    """Set up a config entry."""
    return await opp.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(opp, entry):
    """Unload a config entry."""
    return await opp.data[DOMAIN].async_unload_entry(entry)


class GeolocationEvent(Entity):
    """This represents an external event with an associated geolocation."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.distance is not None:
            return round(self.distance, 1)
        return None

    @property
    def source(self) -> str:
        """Return source value of this external event."""
        raise NotImplementedError

    @property
    def distance(self) -> Optional[float]:
        """Return distance value of this external event."""
        return None

    @property
    def latitude(self) -> Optional[float]:
        """Return latitude value of this external event."""
        return None

    @property
    def longitude(self) -> Optional[float]:
        """Return longitude value of this external event."""
        return None

    @property
    def state_attributes(self):
        """Return the state attributes of this external event."""
        data = {}
        if self.latitude is not None:
            data[ATTR_LATITUDE] = round(self.latitude, 5)
        if self.longitude is not None:
            data[ATTR_LONGITUDE] = round(self.longitude, 5)
        if self.source is not None:
            data[ATTR_SOURCE] = self.source
        return data
