"""Provide configuration end points for scripts."""
from openpeerpower.components.script import DOMAIN, SCRIPT_ENTRY_SCHEMA
from openpeerpower.const import SERVICE_RELOAD
import openpeerpower.helpers.config_validation as cv

from . import EditKeyBasedConfigView

CONFIG_PATH = 'scripts.yaml'


async def async_setup(opp):
    """Set up the script config API."""
    async def hook(opp):
        """post_write_hook for Config View that reloads scripts."""
        await opp.services.async_call(DOMAIN, SERVICE_RELOAD)

    opp.http.register_view(EditKeyBasedConfigView(
        'script', 'config', CONFIG_PATH, cv.slug, SCRIPT_ENTRY_SCHEMA,
        post_write_hook=hook
    ))
    return True
