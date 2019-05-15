"""Plugable auth modules for Open Peer Power."""
import importlib
import logging
import types
from typing import Any, Dict, Optional

import voluptuous as vol
from voluptuous.humanize import humanize_error

from openpeerpower import requirements, data_entry_flow
from openpeerpower.const import CONF_ID, CONF_NAME, CONF_TYPE
from openpeerpower.core import OpenPeerPower
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.util.decorator import Registry

MULTI_FACTOR_AUTH_MODULES = Registry()

MULTI_FACTOR_AUTH_MODULE_SCHEMA = vol.Schema({
    vol.Required(CONF_TYPE): str,
    vol.Optional(CONF_NAME): str,
    # Specify ID if you have two mfa auth module for same type.
    vol.Optional(CONF_ID): str,
}, extra=vol.ALLOW_EXTRA)

DATA_REQS = 'mfa_auth_module_reqs_processed'

_LOGGER = logging.getLogger(__name__)


class MultiFactorAuthModule:
    """Multi-factor Auth Module of validation function."""

    DEFAULT_TITLE = 'Unnamed auth module'
    MAX_RETRY_TIME = 3

    def __init__(self, opp: OpenPeerPower, config: Dict[str, Any]) -> None:
        """Initialize an auth module."""
        self.opp = opp
        self.config = config

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        """Return id of the auth module.

        Default is same as type
        """
        return self.config.get(CONF_ID, self.type)

    @property
    def type(self) -> str:
        """Return type of the module."""
        return self.config[CONF_TYPE]  # type: ignore

    @property
    def name(self) -> str:
        """Return the name of the auth module."""
        return self.config.get(CONF_NAME, self.DEFAULT_TITLE)

    # Implement by extending class

    @property
    def input_schema(self) -> vol.Schema:
        """Return a voluptuous schema to define mfa auth module's input."""
        raise NotImplementedError

    async def async_setup_flow(self, user_id: str) -> 'SetupFlow':
        """Return a data entry flow handler for setup module.

        Mfa module should extend SetupFlow
        """
        raise NotImplementedError

    async def async_setup_user(self, user_id: str, setup_data: Any) -> Any:
        """Set up user for mfa auth module."""
        raise NotImplementedError

    async def async_depose_user(self, user_id: str) -> None:
        """Remove user from mfa module."""
        raise NotImplementedError

    async def async_is_user_setup(self, user_id: str) -> bool:
        """Return whether user is setup."""
        raise NotImplementedError

    async def async_validate(
            self, user_id: str, user_input: Dict[str, Any]) -> bool:
        """Return True if validation passed."""
        raise NotImplementedError


class SetupFlow(data_entry_flow.FlowHandler):
    """Handler for the setup flow."""

    def __init__(self, auth_module: MultiFactorAuthModule,
                 setup_schema: vol.Schema,
                 user_id: str) -> None:
        """Initialize the setup flow."""
        self._auth_module = auth_module
        self._setup_schema = setup_schema
        self._user_id = user_id

    async def async_step_init(
            self, user_input: Optional[Dict[str, str]] = None) \
            -> Dict[str, Any]:
        """Handle the first step of setup flow.

        Return self.async_show_form(step_id='init') if user_input is None.
        Return self.async_create_entry(data={'result': result}) if finish.
        """
        errors = {}  # type: Dict[str, str]

        if user_input:
            result = await self._auth_module.async_setup_user(
                self._user_id, user_input)
            return self.async_create_entry(
                title=self._auth_module.name,
                data={'result': result}
            )

        return self.async_show_form(
            step_id='init',
            data_schema=self._setup_schema,
            errors=errors
        )


async def auth_mfa_module_from_config(
        opp: OpenPeerPower, config: Dict[str, Any]) \
        -> MultiFactorAuthModule:
    """Initialize an auth module from a config."""
    module_name = config[CONF_TYPE]
    module = await _load_mfa_module(opp, module_name)

    try:
        config = module.CONFIG_SCHEMA(config)  # type: ignore
    except vol.Invalid as err:
        _LOGGER.error('Invalid configuration for multi-factor module %s: %s',
                      module_name, humanize_error(config, err))
        raise

    return MULTI_FACTOR_AUTH_MODULES[module_name](opp, config)  # type: ignore


async def _load_mfa_module(opp: OpenPeerPower, module_name: str) \
        -> types.ModuleType:
    """Load an mfa auth module."""
    module_path = 'openpeerpower.auth.mfa_modules.{}'.format(module_name)

    try:
        module = importlib.import_module(module_path)
    except ImportError as err:
        _LOGGER.error('Unable to load mfa module %s: %s', module_name, err)
        raise OpenPeerPowerError('Unable to load mfa module {}: {}'.format(
            module_name, err))

    if opp.config.skip_pip or not hasattr(module, 'REQUIREMENTS'):
        return module

    processed = opp.data.get(DATA_REQS)
    if processed and module_name in processed:
        return module

    processed = opp.data[DATA_REQS] = set()

    # https://github.com/python/mypy/issues/1424
    req_success = await requirements.async_process_requirements(
        opp, module_path, module.REQUIREMENTS)    # type: ignore

    if not req_success:
        raise OpenPeerPowerError(
            'Unable to process requirements of mfa module {}'.format(
                module_name))

    processed.add(module_name)
    return module
