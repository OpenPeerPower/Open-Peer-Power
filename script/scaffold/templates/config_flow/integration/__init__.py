"""The NEW_NAME integration."""
import asyncio

import voluptuous as vol

from openpeerpower.config_entries import ConfigEntry
from openpeerpower.core import OpenPeerPower

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["light"]


async def async_setup(opp: OpenPeerPower, config: dict):
    """Set up the NEW_NAME component."""
    return True


async def async_setup_entry(opp: OpenPeerPower, entry: ConfigEntry):
    """Set up NEW_NAME from a config entry."""
    # TODO Store an API object for your platforms to access
    # opp.data[DOMAIN][entry.entry_id] = MyApi(...)

    for component in PLATFORMS:
        opp.async_create_task(
            opp.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(opp: OpenPeerPower, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                opp.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        opp.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
