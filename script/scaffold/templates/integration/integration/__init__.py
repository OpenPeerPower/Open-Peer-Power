"""The NEW_NAME integration."""
import voluptuous as vol

from openpeerpower.core import OpenPeerPower

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): {}}, extra=vol.ALLOW_EXTRA)


async def async_setup(opp: OpenPeerPower, config: dict):
    """Set up the NEW_NAME integration."""
    return True
