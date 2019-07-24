"""Handle the auth of a connection."""
import voluptuous as vol
from voluptuous.humanize import humanize_error

from openpeerpower.auth.providers import legacy_api_password
from openpeerpower.components.http.ban import (
    process_wrong_login,
    process_success_login,
)
from openpeerpower.const import __version__

from .connection import ActiveConnection
from .error import Disconnect
import jwt
from openpeerpower.auth.util import generate_secret

TYPE_AUTH = 'auth'
TYPE_AUTH_INVALID = 'auth_invalid'
TYPE_AUTH_OK = 'auth_ok'
TYPE_AUTH_REQUIRED = 'auth_required'
TYPE_AUTH_CODE = 'auth_code'
TYPE_AUTH_TOKEN = 'auth_token'
DATA_SIGN_SECRET = 'http.auth.sign_secret'
SIGN_QUERY_PARAM = 'authSig'

AUTH_MESSAGE_SCHEMA = vol.Schema({
    vol.Required('type'): TYPE_AUTH,
    vol.Exclusive('api_password', 'auth'): str,
    vol.Exclusive('access_token', 'auth'): str,
})


def auth_ok_message():
    """Return an auth_ok message."""
    return {
        'type': TYPE_AUTH_OK,
        'ha_version': __version__,
    }


def auth_required_message():
    """Return an auth_required message."""
    return {
        'type': TYPE_AUTH_REQUIRED,
        'ha_version': __version__,
    }


def auth_invalid_message(message):
    """Return an auth_invalid message."""
    return {
        'type': TYPE_AUTH_INVALID,
        'message': message,
    }


class AuthPhase:
    """Connection that requires client to authenticate first."""

    def __init__(self, logger, opp, send_message, request):
        """Initialize the authentiated connection."""
        self._opp = opp
        self._send_message = send_message
        self._logger = logger
        self._request = request
        self._authenticated = False
        self._connection = None

    async def async_handle(self, msg):
        """Handle authentication."""
        if msg['type'] == 'register':
            provider = _async_get_opp_provider(self._opp)
            await provider.async_initialize()   
            user = await self._opp.auth.async_create_user(
                name=msg['name'],
            )
            await self._opp.async_add_executor_job(
                provider.data.add_auth, msg['username'], msg['password'])
            credentials = await provider.async_get_or_create_credentials({
                'username': msg['username']
            })
            await provider.data.async_save()
            await self._opp.auth.async_link_user(user, credentials)
            if 'person' in self._opp.config.components:
                await self._opp.components.person.async_create_person(
                    data['name'], user_id=user.id
                )
            # Return authorization token for fetching tokens and connect
            # during onboarding.
            auth_code = self._opp.components.auth.create_auth_code(
                msg['client_id'], user
            )
            self._send_message(
                {'type': TYPE_AUTH_CODE,
                 'auth_code': auth_code,
                }
            )
            return
        
        if msg['type'] == 'authorize':
            user = await self._opp.auth.async_get_user(, msg['user_id'])
            refresh_token = await self._opp.auth.async_create_refresh_token(user, msg['client_id'])
            
        try:
            msg = AUTH_MESSAGE_SCHEMA(msg)
        except vol.Invalid as err:
            error_msg = 'Auth message incorrectly formatted: {}'.format(
                humanize_error(msg, err))
            self._logger.warning(error_msg)
            self._send_message(auth_invalid_message(error_msg))
            raise Disconnect

        if 'access_token' in msg:
            self._logger.debug("Received access_token")
            # Temprarily pass through any token
            #refresh_token = 'XYZ'
            refresh_token = \
                await self._opp.auth.async_validate_access_token(
                    msg['access_token'])
            if refresh_token is not None:
                return await self._async_finish_auth(
                    refresh_token.user, refresh_token)

        elif self._opp.auth.support_legacy and 'api_password' in msg:
            self._logger.info(
                "Received api_password, it is going to deprecate, please use"
                " access_token instead. For instructions, see https://"
                "developers.open-peer-power.io/docs/en/external_api_websocket"
                ".html#authentication-phase"
            )
            user = await legacy_api_password.async_validate_password(
                self._opp, msg['api_password'])
            if user is not None:
                return await self._async_finish_auth(user, None)

        self._send_message(auth_invalid_message(
            'Invalid access token or password'))
        await process_wrong_login(self._request)
        raise Disconnect

    async def _async_finish_auth(self, user, refresh_token) \
            -> ActiveConnection:
        """Create an active connection."""
        self._logger.debug("Auth OK")
        await process_success_login(self._request)
        self._send_message(auth_ok_message())
        return ActiveConnection(
            self._logger, self._opp, self._send_message, user, refresh_token)

def _async_get_opp_provider(opp):
    """Get the Open Peer Power auth provider."""
    for prv in opp.auth.auth_providers:
        if prv.type == 'openpeerpower':
            return prv

    raise RuntimeError('No Open Peer Power provider found')
