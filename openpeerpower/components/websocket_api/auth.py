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
import json
from datetime import timedelta
from openpeerpower.auth.util import generate_secret
from openpeerpower.auth.providers.openpeerpower import (
    InvalidAuth,
    NoUsers
)
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

def auth_ok_message(access_token = ''):
    """Return an auth_ok message."""
    return {
        'type': TYPE_AUTH_OK,
        'opp_version': __version__,
        'access_token': access_token
    }


def auth_required_message():
    """Return an auth_required message."""
    return {
        'type': TYPE_AUTH_REQUIRED,
        'opp_version': __version__,
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
        """Initialize the authenticated connection."""
        self._opp = opp
        self._send_message = send_message
        self._logger = logger
        self._request = request
        self._authenticated = False
        self._connection = None

    async def async_handle(self, msg):
        """Handle authentication."""
        if msg['type'] == 'auth':
            self._logger.debug("Received access_token")
            refresh_token = \
                await self._opp.auth.async_validate_access_token(
                    msg['access_token'])
            if refresh_token is not None:
                return await self._async_finish_auth(
                    refresh_token.user, refresh_token)

        if msg['type'] == 'login':
            provider = _async_get_opp_provider(self._opp)
            try:
                await provider.async_validate_login(
                    msg['username'], msg['api_password'])

                # password is valid return authorization token for fetching tokens and connect
                user = await self._opp.auth.async_get_user_by_credentials(
                    await provider.async_get_or_create_credentials({
                    'username': msg['username']
                    })
                )
                for refresh_token in user.refresh_tokens.values():
                    if refresh_token.client_name == msg['username']:
                        break
                if refresh_token is not None:
                    return await self._async_finish_auth(
                        refresh_token.user, refresh_token)
            except InvalidAuth:
                print("Auth invalid")
                return
            except NoUsers:
                await provider.async_initialize()   
                user = await self._opp.auth.async_create_user(
                    name=msg['name'],
                )
                await self._opp.async_add_executor_job(
                    provider.data.add_auth, msg['username'], msg['api_password'])
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

                refresh_token = await self._opp.auth.async_create_refresh_token(
                    user, msg['client_id'],msg['username'],
                    token_type = 'long_lived_access_token',
                    access_token_expiration=timedelta(days=365)
                    )
                if refresh_token is not None:
                    return await self._async_finish_auth(
                        refresh_token.user, refresh_token)

        self._send_message(auth_invalid_message(
            'Invalid access token or password'))
        await process_wrong_login(self._request)
        raise Disconnect

    async def _async_finish_auth(self, user, refresh_token) \
            -> ActiveConnection:
        """Create an active connection."""
        self._logger.debug("Auth OK")
        await process_success_login(self._request)
        access_token = self._opp.auth.async_create_access_token(refresh_token)
        self._send_message(auth_ok_message(access_token))
        return ActiveConnection(
            self._logger, self._opp, self._send_message, user, refresh_token)

def _async_get_opp_provider(opp):
    """Get the Open Peer Power auth provider."""
    for prv in opp.auth.auth_providers:
        if prv.type == 'openpeerpower':
            return prv

    raise RuntimeError('No Open Peer Power provider found')
