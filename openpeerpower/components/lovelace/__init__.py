"""Support for the Lovelace UI."""
from functools import wraps
import logging
import os
import time

import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.util.yaml import load_yaml

_LOGGER = logging.getLogger(__name__)

DOMAIN = "lovelace"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
CONF_MODE = "mode"
MODE_YAML = "yaml"
MODE_STORAGE = "storage"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_MODE, default=MODE_STORAGE): vol.All(
                    vol.Lower, vol.In([MODE_YAML, MODE_STORAGE])
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

EVENT_LOVELACE_UPDATED = "lovelace_updated"

LOVELACE_CONFIG_FILE = "ui-lovelace.yaml"

WS_TYPE_GET_LOVELACE_UI = "lovelace/config"
WS_TYPE_SAVE_CONFIG = "lovelace/config/save"

SCHEMA_GET_LOVELACE_UI = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_GET_LOVELACE_UI,
        vol.Optional("force", default=False): bool,
    }
)

SCHEMA_SAVE_CONFIG = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_SAVE_CONFIG,
        vol.Required("config"): vol.Any(str, dict),
    }
)


class ConfigNotFound(OpenPeerPowerError):
    """When no config available."""


async def async_setup(opp, config):
    """Set up the Lovelace commands."""
    # Pass in default to `get` because defaults not set if loaded as dep
    mode = config.get(DOMAIN, {}).get(CONF_MODE, MODE_STORAGE)

    if mode == MODE_YAML:
        opp.data[DOMAIN] = LovelaceYAML(opp)
    else:
        opp.data[DOMAIN] = LovelaceStorage(opp)

    opp.components.websocket_api.async_register_command(
        WS_TYPE_GET_LOVELACE_UI, websocket_lovelace_config, SCHEMA_GET_LOVELACE_UI
    )

    opp.components.websocket_api.async_register_command(
        WS_TYPE_SAVE_CONFIG, websocket_lovelace_save_config, SCHEMA_SAVE_CONFIG
    )

    opp.components.system_health.async_register_info(DOMAIN, system_health_info)

    return True


class LovelaceStorage:
    """Class to handle Storage based Lovelace config."""

    def __init__(self, opp):
        """Initialize Lovelace config based on storage helper."""
        self._store = opp.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
        self._data = None
        self._opp = opp

    async def async_get_info(self):
        """Return the YAML storage mode."""
        if self._data is None:
            await self._load()

        if self._data["config"] is None:
            return {"mode": "auto-gen"}

        return _config_info("storage", self._data["config"])

    async def async_load(self, force):
        """Load config."""
        if self._data is None:
            await self._load()

        config = self._data["config"]

        if config is None:
            raise ConfigNotFound

        return config

    async def async_save(self, config):
        """Save config."""
        if self._data is None:
            await self._load()
        self._data["config"] = config
        self._opp.bus.async_fire(EVENT_LOVELACE_UPDATED)
        await self._store.async_save(self._data)

    async def _load(self):
        """Load the config."""
        data = await self._store.async_load()
        self._data = data if data else {"config": None}


class LovelaceYAML:
    """Class to handle YAML-based Lovelace config."""

    def __init__(self, opp):
        """Initialize the YAML config."""
        self.opp = opp
        self._cache = None

    async def async_get_info(self):
        """Return the YAML storage mode."""
        try:
            config = await self.async_load(False)
        except ConfigNotFound:
            return {
                "mode": "yaml",
                "error": "{} not found".format(
                    self.opp.config.path(LOVELACE_CONFIG_FILE)
                ),
            }

        return _config_info("yaml", config)

    async def async_load(self, force):
        """Load config."""
        is_updated, config = await self.opp.async_add_executor_job(
            self._load_config, force
        )
        if is_updated:
            self.opp.bus.async_fire(EVENT_LOVELACE_UPDATED)
        return config

    def _load_config(self, force):
        """Load the actual config."""
        fname = self.opp.config.path(LOVELACE_CONFIG_FILE)
        # Check for a cached version of the config
        if not force and self._cache is not None:
            config, last_update = self._cache
            modtime = os.path.getmtime(fname)
            if config and last_update > modtime:
                return False, config

        is_updated = self._cache is not None

        try:
            config = load_yaml(fname)
        except FileNotFoundError:
            raise ConfigNotFound from None

        self._cache = (config, time.time())
        return is_updated, config

    async def async_save(self, config):
        """Save config."""
        raise OpenPeerPowerError("Not supported")


def handle_yaml_errors(func):
    """Handle error with WebSocket calls."""

    @wraps(func)
    async def send_with_error_handling(opp, connection, msg):
        error = None
        try:
            result = await func(opp, connection, msg)
        except ConfigNotFound:
            error = "config_not_found", "No config found."
        except OpenPeerPowerError as err:
            error = "error", str(err)

        if error is not None:
            connection.send_error(msg["id"], *error)
            return

        if msg is not None:
            await connection.send_big_result(msg["id"], result)
        else:
            connection.send_result(msg["id"], result)

    return send_with_error_handling


@websocket_api.async_response
@handle_yaml_errors
async def websocket_lovelace_config(opp, connection, msg):
    """Send Lovelace UI config over WebSocket configuration."""
    return await opp.data[DOMAIN].async_load(msg["force"])


@websocket_api.async_response
@handle_yaml_errors
async def websocket_lovelace_save_config(opp, connection, msg):
    """Save Lovelace UI configuration."""
    await opp.data[DOMAIN].async_save(msg["config"])


async def system_health_info(opp):
    """Get info for the info page."""
    return await opp.data[DOMAIN].async_get_info()


def _config_info(mode, config):
    """Generate info about the config."""
    return {
        "mode": mode,
        "resources": len(config.get("resources", [])),
        "views": len(config.get("views", [])),
    }
