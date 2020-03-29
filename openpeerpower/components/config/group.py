"""Provide configuration end points for Groups."""
from openpeerpower.components.group import DOMAIN, GROUP_SCHEMA
from openpeerpower.config import GROUP_CONFIG_PATH
from openpeerpower.const import SERVICE_RELOAD
import openpeerpower.helpers.config_validation as cv

from . import EditKeyBasedConfigView


async def async_setup(opp):
    """Set up the Group config API."""

    async def hook(action, config_key):
        """post_write_hook for Config View that reloads groups."""
        await opp.services.async_call(DOMAIN, SERVICE_RELOAD)

    opp.http.register_view(
        EditKeyBasedConfigView(
            "group",
            "config",
            GROUP_CONFIG_PATH,
            cv.slug,
            GROUP_SCHEMA,
            post_write_hook=hook,
        )
    )
    return True
