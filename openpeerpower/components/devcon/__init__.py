"""Support for the Devcon UI."""
from functools import wraps
import logging
import os
import time

import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.util.yaml import load_yaml

_LOGGER = logging.getLogger(__name__)

DOMAIN = "devcon"
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

EVENT_LOVELACE_UPDATED = "devcon_updated"

LOVELACE_CONFIG_FILE = "ui-devcon.yaml"


class ConfigNotFound(OpenPeerPowerError):
    """When no config available."""


async def async_setup(opp, config):
    """Set up the Devcon commands."""
    # Pass in default to `get` because defaults not set if loaded as dep
    mode = config.get(DOMAIN, {}).get(CONF_MODE, MODE_STORAGE)

    opp.components.frontend.async_register_built_in_panel(
        DOMAIN, config={"mode": mode}
    )

    if mode == MODE_YAML:
        opp.data[DOMAIN] = DevconYAML(opp)
    else:
        opp.data[DOMAIN] = DevconStorage(opp)

    opp.components.websocket_api.async_register_command(websocket_devcon_config)

    opp.components.websocket_api.async_register_command(websocket_devcon_save_config)

    opp.components.websocket_api.async_register_command(
        websocket_devcon_delete_config
    )

    opp.components.system_health.async_register_info(DOMAIN, system_health_info)

    return True


class DevconStorage:
    """Class to handle Storage based Devcon config."""

    def __init__(self, opp):
        """Initialize Devcon config based on storage helper."""
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
        if self._opp.config.safe_mode:
            raise ConfigNotFound

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

    async def async_delete(self):
        """Delete config."""
        await self.async_save(None)

    async def _load(self):
        """Load the config."""
        data = await self._store.async_load()
        self._data = data if data else {"config": None}


class DevconYAML:
    """Class to handle YAML-based Devcon config."""

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

    async def async_delete(self):
        """Delete config."""
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
@websocket_api.websocket_command(
    {"type": "devcon/config", vol.Optional("force", default=False): bool}
)
@handle_yaml_errors
async def websocket_devcon_config(opp, connection, msg):
    """Send Devcon UI config over WebSocket configuration."""
    return await opp.data[DOMAIN].async_load(msg["force"])


@websocket_api.async_response
@websocket_api.websocket_command(
    {"type": "devcon/config/save", "config": vol.Any(str, dict)}
)
@handle_yaml_errors
async def websocket_devcon_save_config(opp, connection, msg):
    """Save Devcon UI configuration."""
    await opp.data[DOMAIN].async_save(msg["config"])


@websocket_api.async_response
@websocket_api.websocket_command({"type": "devcon/config/delete"})
@handle_yaml_errors
async def websocket_devcon_delete_config(opp, connection, msg):
    """Delete Devcon UI configuration."""
    await opp.data[DOMAIN].async_delete()


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
