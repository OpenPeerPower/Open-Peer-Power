"""The NEW_NAME integration."""
import asyncio

import voluptuous as vol

from openpeerpower.config_entries import ConfigEntry
from openpeerpower.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from openpeerpower.core import OpenPeerPower
from openpeerpower.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
)

from . import api, config_flow
from .const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["light"]


async def async_setup(opp: OpenPeerPower, config: dict):
    """Set up the NEW_NAME component."""
    opp.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    config_flow.OAuth2FlowHandler.async_register_implementation(
        opp,
        config_entry_oauth2_flow.LocalOAuth2Implementation(
            opp,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        ),
    )

    return True


async def async_setup_entry(opp: OpenPeerPower, entry: ConfigEntry):
    """Set up NEW_NAME from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(opp, entry)
    )

    session = config_entry_oauth2_flow.OAuth2Session(opp, entry, implementation)

    # If using a requests-based API lib
    opp.data[DOMAIN][entry.entry_id] = api.ConfigEntryAuth(opp, entry, session)

    # If using an aiohttp-based API lib
    opp.data[DOMAIN][entry.entry_id] = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(opp), session
    )

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
