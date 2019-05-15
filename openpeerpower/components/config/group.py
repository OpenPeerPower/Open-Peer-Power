"""Provide configuration end points for Groups."""
from openpeerpower.components.group import DOMAIN, GROUP_SCHEMA
from openpeerpower.const import SERVICE_RELOAD
import openpeerpower.helpers.config_validation as cv

from . import EditKeyBasedConfigView

CONFIG_PATH = 'groups.yaml'


async def async_setup(opp):
    """Set up the Group config API."""
    async def hook(opp):
        """post_write_hook for Config View that reloads groups."""
        await opp.services.async_call(DOMAIN, SERVICE_RELOAD)

    opp.http.register_view(EditKeyBasedConfigView(
        'group', 'config', CONFIG_PATH, cv.slug, GROUP_SCHEMA,
        post_write_hook=hook
    ))
    return True
