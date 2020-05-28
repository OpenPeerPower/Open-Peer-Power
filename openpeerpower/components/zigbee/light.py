"""Support for Zigbee lights."""
import voluptuous as vol

from openpeerpower.components.light import Light

from . import PLATFORM_SCHEMA, ZigBeeDigitalOut, ZigBeeDigitalOutConfig

CONF_ON_STATE = "on_state"

DEFAULT_ON_STATE = "high"
STATES = ["high", "low"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_ON_STATE, default=DEFAULT_ON_STATE): vol.In(STATES)}
)


def setup_platform(opp, config, add_entities, discovery_info=None):
    """Create and add an entity based on the configuration."""
    add_entities([ZigBeeLight(opp, ZigBeeDigitalOutConfig(config))])


class ZigBeeLight(ZigBeeDigitalOut, Light):
    """Use ZigBeeDigitalOut as light."""

    pass
