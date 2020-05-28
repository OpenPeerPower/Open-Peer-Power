"""Implement the Ingress Panel feature for Opp.io Add-ons."""
import asyncio
import logging

from aiohttp import web

from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.helpers.typing import OpenPeerPowerType

from .const import ATTR_ADMIN, ATTR_ENABLE, ATTR_ICON, ATTR_PANELS, ATTR_TITLE
from .handler import OppioAPIError

_LOGGER = logging.getLogger(__name__)


async def async_setup_addon_panel(opp: OpenPeerPowerType, oppio):
    """Add-on Ingress Panel setup."""
    oppio_addon_panel = OppIOAddonPanel(opp, oppio)
    opp.http.register_view(oppio_addon_panel)

    # If panels are exists
    panels = await oppio_addon_panel.get_panels()
    if not panels:
        return

    # Register available panels
    jobs = []
    for addon, data in panels.items():
        if not data[ATTR_ENABLE]:
            continue
        jobs.append(_register_panel(opp, addon, data))

    if jobs:
        await asyncio.wait(jobs)


class OppIOAddonPanel(OpenPeerPowerView):
    """Opp.io view to handle base part."""

    name = "api:oppio_push:panel"
    url = "/api/oppio_push/panel/{addon}"

    def __init__(self, opp, oppio):
        """Initialize WebView."""
        self.opp = opp
        self.oppio = oppio

    async def post(self, request, addon):
        """Handle new add-on panel requests."""
        panels = await self.get_panels()

        # Panel exists for add-on slug
        if addon not in panels or not panels[addon][ATTR_ENABLE]:
            _LOGGER.error("Panel is not enable for %s", addon)
            return web.Response(status=400)
        data = panels[addon]

        # Register panel
        await _register_panel(self.opp, addon, data)
        return web.Response()

    async def delete(self, request, addon):
        """Handle remove add-on panel requests."""
        self.opp.components.frontend.async_remove_panel(addon)
        return web.Response()

    async def get_panels(self):
        """Return panels add-on info data."""
        try:
            data = await self.oppio.get_ingress_panels()
            return data[ATTR_PANELS]
        except OppioAPIError as err:
            _LOGGER.error("Can't read panel info: %s", err)
        return {}


def _register_panel(opp, addon, data):
    """Init coroutine to register the panel.

    Return coroutine.
    """
    return opp.components.panel_custom.async_register_panel(
        frontend_url_path=addon,
        webcomponent_name="oppio-main",
        sidebar_title=data[ATTR_TITLE],
        sidebar_icon=data[ATTR_ICON],
        js_url="/api/oppio/app/entrypoint.js",
        embed_iframe=True,
        require_admin=data[ATTR_ADMIN],
        config={"ingress": addon},
    )
