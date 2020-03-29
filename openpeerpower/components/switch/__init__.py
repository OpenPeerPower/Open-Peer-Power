"""Component to interface with switches that can be controlled remotely."""
from datetime import timedelta
import logging

import voluptuous as vol

from openpeerpower.const import (
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from openpeerpower.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from openpeerpower.helpers.entity import ToggleEntity
from openpeerpower.helpers.entity_component import EntityComponent
from openpeerpower.loader import bind_opp

# mypy: allow-untyped-defs, no-check-untyped-defs

DOMAIN = "switch"
SCAN_INTERVAL = timedelta(seconds=30)

ENTITY_ID_FORMAT = DOMAIN + ".{}"

ATTR_TODAY_ENERGY_KWH = "today_energy_kwh"
ATTR_CURRENT_POWER_W = "current_power_w"

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)

PROP_TO_ATTR = {
    "current_power_w": ATTR_CURRENT_POWER_W,
    "today_energy_kwh": ATTR_TODAY_ENERGY_KWH,
}

DEVICE_CLASS_OUTLET = "outlet"
DEVICE_CLASS_SWITCH = "switch"

DEVICE_CLASSES = [DEVICE_CLASS_OUTLET, DEVICE_CLASS_SWITCH]

DEVICE_CLASSES_SCHEMA = vol.All(vol.Lower, vol.In(DEVICE_CLASSES))

_LOGGER = logging.getLogger(__name__)


@bind_opp
def is_on(opp, entity_id):
    """Return if the switch is on based on the statemachine.

    Async friendly.
    """
    return opp.states.is_state(entity_id, STATE_ON)


async def async_setup(opp, config):
    """Track states and offer events for switches."""
    component = opp.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, opp, SCAN_INTERVAL
    )
    await component.async_setup(config)

    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")
    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")
    component.async_register_entity_service(SERVICE_TOGGLE, {}, "async_toggle")

    return True


async def async_setup_entry(opp, entry):
    """Set up a config entry."""
    return await opp.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(opp, entry):
    """Unload a config entry."""
    return await opp.data[DOMAIN].async_unload_entry(entry)


class SwitchDevice(ToggleEntity):
    """Representation of a switch."""

    @property
    def current_power_w(self):
        """Return the current power usage in W."""
        return None

    @property
    def today_energy_kwh(self):
        """Return the today total energy usage in kWh."""
        return None

    @property
    def is_standby(self):
        """Return true if device is in standby."""
        return None

    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        data = {}

        for prop, attr in PROP_TO_ATTR.items():
            value = getattr(self, prop)
            if value:
                data[attr] = value

        return data

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return None
