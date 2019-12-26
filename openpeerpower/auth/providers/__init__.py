"""Auth providers for Open Peer Power."""
import importlib
import logging
import types
from typing import Any, Dict, List, Optional

import voluptuous as vol
from voluptuous.humanize import humanize_error

from openpeerpower import data_entry_flow, requirements
from openpeerpower.core import callback, OpenPeerPower
from openpeerpower.const import CONF_ID, CONF_NAME, CONF_TYPE
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.util import dt as dt_util
from openpeerpower.util.decorator import Registry

from ..auth_store import AuthStore
from ..models import Credentials, User, UserMeta  # noqa: F401

_LOGGER = logging.getLogger(__name__)
DATA_REQS = 'auth_prov_reqs_processed'

AUTH_PROVIDERS = Registry()

AUTH_PROVIDER_SCHEMA = vol.Schema({
    vol.Required(CONF_TYPE): str,
    vol.Optional(CONF_NAME): str,
    # Specify ID if you have two auth providers for same type.
    vol.Optional(CONF_ID): str,
}, extra=vol.ALLOW_EXTRA)


class AuthProvider:
    """Provider of user authentication."""

    DEFAULT_TITLE = 'Unnamed auth provider'

    def __init__(self, opp: OpenPeerPower, store: AuthStore,
                 config: Dict[str, Any]) -> None:
        """Initialize an auth provider."""
        self.opp = opp
        self.store = store
        self.config = config

    @property
    def id(self) -> Optional[str]:  # pylint: disable=invalid-name
        """Return id of the auth provider.

        Optional, can be None.
        """
        return self.config.get(CONF_ID)

    @property
    def type(self) -> str:
        """Return type of the provider."""
        return self.config[CONF_TYPE]  # type: ignore

    @property
    def name(self) -> str:
        """Return the name of the auth provider."""
        return self.config.get(CONF_NAME, self.DEFAULT_TITLE)

    async def async_credentials(self) -> List[Credentials]:
        """Return all credentials of this provider."""
        users = await self.store.async_get_users()
        return [
            credentials
            for user in users
            for credentials in user.credentials
            if (credentials.auth_provider_type == self.type and
                credentials.auth_provider_id == self.id)
        ]

    @callback
    def async_create_credentials(self, data: Dict[str, str]) -> Credentials:
        """Create credentials."""
        return Credentials(
            auth_provider_type=self.type,
            auth_provider_id=self.id,
            data=data,
        )

    # Implement by extending class

    async def async_login_flow(self, context: Optional[Dict]) -> 'LoginFlow':
        """Return the data flow for logging in with auth provider.

        Auth provider should extend LoginFlow and return an instance.
        """
        raise NotImplementedError

    async def async_get_or_create_credentials(
            self, flow_result: Dict[str, str]) -> Credentials:
        """Get credentials based on the flow result."""
        raise NotImplementedError

    async def async_user_meta_for_credentials(
            self, credentials: Credentials) -> UserMeta:
        """Return extra user metadata for credentials.

        Will be used to populate info when creating a new user.
        """
        raise NotImplementedError


async def auth_provider_from_config(
        opp: OpenPeerPower, store: AuthStore,
        config: Dict[str, Any]) -> AuthProvider:
    """Initialize an auth provider from a config."""
    provider_name = config[CONF_TYPE]
    module = await load_auth_provider_module(opp, provider_name)

    try:
        config = module.CONFIG_SCHEMA(config)  # type: ignore
    except vol.Invalid as err:
        _LOGGER.error('Invalid configuration for auth provider %s: %s',
                      provider_name, humanize_error(config, err))
        raise

    return AUTH_PROVIDERS[provider_name](opp, store, config)  # type: ignore


async def load_auth_provider_module(
        opp: OpenPeerPower, provider: str) -> types.ModuleType:
    """Load an auth provider."""
    try:
        module = importlib.import_module(
            'openpeerpower.auth.providers.{}'.format(provider))
    except ImportError as err:
        _LOGGER.error('Unable to load auth provider %s: %s', provider, err)
        raise OpenPeerPowerError('Unable to load auth provider {}: {}'.format(
            provider, err))

    if opp.config.skip_pip or not hasattr(module, 'REQUIREMENTS'):
        return module

    processed = opp.data.get(DATA_REQS)

    if processed is None:
        processed = opp.data[DATA_REQS] = set()
    elif provider in processed:
        return module

    # https://github.com/python/mypy/issues/1424
    reqs = module.REQUIREMENTS  # type: ignore
    req_success = await requirements.async_process_requirements(
        opp, 'auth provider {}'.format(provider), reqs)

    if not req_success:
        raise OpenPeerPowerError(
            'Unable to process requirements of auth provider {}'.format(
                provider))

    processed.add(provider)
    return module


class LoginFlow(data_entry_flow.FlowHandler):
    """Handler for the login flow."""

    def __init__(self, auth_provider: AuthProvider) -> None:
        """Initialize the login flow."""
        self._auth_provider = auth_provider
        self._auth_module_id = None  # type: Optional[str]
        self._auth_manager = auth_provider.opp.auth  # type: ignore
        self.created_at = dt_util.utcnow()
        self.user = None  # type: Optional[User]

    async def async_step_init(
            self, user_input: Optional[Dict[str, str]] = None) \
            -> Dict[str, Any]:
        """Handle the first step of login flow.

        Return self.async_show_form(step_id='init') if user_input is None.
        Return await self.async_finish(flow_result) if login init step pass.
        """
        raise NotImplementedError

    async def async_finish(self, flow_result: Any) -> Dict:
        """Handle the pass of login flow."""
        return self.async_create_entry(
            title=self._auth_provider.name,
            data=flow_result
        )
