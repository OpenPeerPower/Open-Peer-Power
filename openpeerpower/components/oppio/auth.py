"""Implement the auth feature from Opp.io for Add-ons."""
from ipaddress import ip_address
import logging
import os

from aiohttp import web
from aiohttp.web_exceptions import (
    HTTPInternalServerError,
    HTTPNotFound,
    HTTPUnauthorized,
)
import voluptuous as vol

from openpeerpower.auth.models import User
from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.components.http.const import KEY_OPP_USER, KEY_REAL_IP
from openpeerpower.components.http.data_validator import RequestDataValidator
from openpeerpower.core import callback
from openpeerpower.exceptions import OpenPeerPowerError
import openpeerpower.helpers.config_validation as cv
from openpeerpower.helpers.typing import OpenPeerPowerType

from .const import ATTR_ADDON, ATTR_PASSWORD, ATTR_USERNAME

_LOGGER = logging.getLogger(__name__)


SCHEMA_API_AUTH = vol.Schema(
    {
        vol.Required(ATTR_USERNAME): cv.string,
        vol.Required(ATTR_PASSWORD): cv.string,
        vol.Required(ATTR_ADDON): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_API_PASSWORD_RESET = vol.Schema(
    {vol.Required(ATTR_USERNAME): cv.string, vol.Required(ATTR_PASSWORD): cv.string},
    extra=vol.ALLOW_EXTRA,
)


@callback
def async_setup_auth_view(opp: OpenPeerPowerType, user: User):
    """Auth setup."""
    oppio_auth = OppIOAuth(opp, user)
    oppio_password_reset = OppIOPasswordReset(opp, user)

    opp.http.register_view(oppio_auth)
    opp.http.register_view(oppio_password_reset)


class OppIOBaseAuth(OpenPeerPowerView):
    """Opp.io view to handle auth requests."""

    def __init__(self, opp: OpenPeerPowerType, user: User):
        """Initialize WebView."""
        self.opp = opp
        self.user = user

    def _check_access(self, request: web.Request):
        """Check if this call is from Supervisor."""
        # Check caller IP
        oppio_ip = os.environ["OPPIO"].split(":")[0]
        if request[KEY_REAL_IP] != ip_address(oppio_ip):
            _LOGGER.error("Invalid auth request from %s", request[KEY_REAL_IP])
            raise HTTPUnauthorized()

        # Check caller token
        if request[KEY_OPP_USER].id != self.user.id:
            _LOGGER.error("Invalid auth request from %s", request[KEY_OPP_USER].name)
            raise HTTPUnauthorized()

    def _get_provider(self):
        """Return Openpeerpower auth provider."""
        prv = self.opp.auth.get_auth_provider("openpeerpower", None)
        if prv is not None:
            return prv

        _LOGGER.error("Can't find Open Peer Power auth.")
        raise HTTPNotFound()


class OppIOAuth(OppIOBaseAuth):
    """Opp.io view to handle auth requests."""

    name = "api:oppio:auth"
    url = "/api/oppio_auth"

    @RequestDataValidator(SCHEMA_API_AUTH)
    async def post(self, request, data):
        """Handle auth requests."""
        self._check_access(request)

        await self._check_login(data[ATTR_USERNAME], data[ATTR_PASSWORD])
        return web.Response(status=200)

    async def _check_login(self, username, password):
        """Check User credentials."""
        provider = self._get_provider()

        try:
            await provider.async_validate_login(username, password)
        except OpenPeerPowerError:
            raise HTTPUnauthorized() from None


class OppIOPasswordReset(OppIOBaseAuth):
    """Opp.io view to handle password reset requests."""

    name = "api:oppio:auth:password:reset"
    url = "/api/oppio_auth/password_reset"

    @RequestDataValidator(SCHEMA_API_PASSWORD_RESET)
    async def post(self, request, data):
        """Handle password reset requests."""
        self._check_access(request)

        await self._change_password(data[ATTR_USERNAME], data[ATTR_PASSWORD])
        return web.Response(status=200)

    async def _change_password(self, username, password):
        """Check User credentials."""
        provider = self._get_provider()

        try:
            await self.opp.async_add_executor_job(
                provider.data.change_password, username, password
            )
            await provider.data.async_save()
        except OpenPeerPowerError:
            raise HTTPInternalServerError()
