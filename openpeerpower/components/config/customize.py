"""Provide configuration end points for Customize."""
from openpeerpower.components.openpeerpower import SERVICE_RELOAD_CORE_CONFIG
from openpeerpower.config import DATA_CUSTOMIZE
from openpeerpower.core import DOMAIN
import openpeerpower.helpers.config_validation as cv

from . import EditKeyBasedConfigView

CONFIG_PATH = "customize.yaml"


async def async_setup(opp):
    """Set up the Customize config API."""

    async def hook(action, config_key):
        """post_write_hook for Config View that reloads groups."""
        await opp.services.async_call(DOMAIN, SERVICE_RELOAD_CORE_CONFIG)

    opp.http.register_view(
        CustomizeConfigView(
            "customize", "config", CONFIG_PATH, cv.entity_id, dict, post_write_hook=hook
        )
    )

    return True


class CustomizeConfigView(EditKeyBasedConfigView):
    """Configure a list of entries."""

    def _get_value(self, opp, data, config_key):
        """Get value."""
        customize = opp.data.get(DATA_CUSTOMIZE, {}).get(config_key) or {}
        return {"global": customize, "local": data.get(config_key, {})}

    def _write_value(self, opp, data, config_key, new_value):
        """Set value."""
        data[config_key] = new_value

        state = opp.states.get(config_key)
        state_attributes = dict(state.attributes)
        state_attributes.update(new_value)
        opp.states.async_set(config_key, state.state, state_attributes)
