"""Component to configure Open Peer Power via an API."""
import asyncio
import importlib
import os

import voluptuous as vol

from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.const import CONF_ID, EVENT_COMPONENT_LOADED
from openpeerpower.core import callback
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.setup import ATTR_COMPONENT
from openpeerpower.util.yaml import dump, load_yaml

DOMAIN = "config"
SECTIONS = (
    "area_registry",
    "auth",
    "auth_provider_openpeerpower",
    "automation",
    "config_entries",
    "core",
    "customize",
    "device_registry",
    "entity_registry",
    "group",
    "script",
    "scene",
)
ON_DEMAND = ("zwave",)
ACTION_CREATE_UPDATE = "create_update"
ACTION_DELETE = "delete"


async def async_setup(opp, config):
    """Set up the config component."""
    opp.components.frontend.async_register_built_in_panel(
        "config", "config", "opp:settings", require_admin=True
    )

    async def setup_panel(panel_name):
        """Set up a panel."""
        panel = importlib.import_module(f".{panel_name}", __name__)

        if not panel:
            return

        success = await panel.async_setup(opp)

        if success:
            key = f"{DOMAIN}.{panel_name}"
            opp.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: key})

    @callback
    def component_loaded(event):
        """Respond to components being loaded."""
        panel_name = event.data.get(ATTR_COMPONENT)
        if panel_name in ON_DEMAND:
            opp.async_create_task(setup_panel(panel_name))

    opp.bus.async_listen(EVENT_COMPONENT_LOADED, component_loaded)

    tasks = [setup_panel(panel_name) for panel_name in SECTIONS]

    for panel_name in ON_DEMAND:
        if panel_name in opp.config.components:
            tasks.append(setup_panel(panel_name))

    if tasks:
        await asyncio.wait(tasks)

    return True


class BaseEditConfigView(OpenPeerPowerView):
    """Configure a Group endpoint."""

    def __init__(
        self,
        component,
        config_type,
        path,
        key_schema,
        data_schema,
        *,
        post_write_hook=None,
        data_validator=None,
    ):
        """Initialize a config view."""
        self.url = f"/api/config/{component}/{config_type}/{{config_key}}"
        self.name = f"api:config:{component}:{config_type}"
        self.path = path
        self.key_schema = key_schema
        self.data_schema = data_schema
        self.post_write_hook = post_write_hook
        self.data_validator = data_validator
        self.mutation_lock = asyncio.Lock()

    def _empty_config(self):
        """Empty config if file not found."""
        raise NotImplementedError

    def _get_value(self, opp, data, config_key):
        """Get value."""
        raise NotImplementedError

    def _write_value(self, opp, data, config_key, new_value):
        """Set value."""
        raise NotImplementedError

    def _delete_value(self, opp, data, config_key):
        """Delete value."""
        raise NotImplementedError

    async def get(self, request, config_key):
        """Fetch device specific config."""
        opp = request.app["opp"]
        async with self.mutation_lock:
            current = await self.read_config(opp)
            value = self._get_value(opp, current, config_key)

        if value is None:
            return self.json_message("Resource not found", 404)

        return self.json(value)

    async def post(self, request, config_key):
        """Validate config and return results."""
        try:
            data = await request.json()
        except ValueError:
            return self.json_message("Invalid JSON specified", 400)

        try:
            self.key_schema(config_key)
        except vol.Invalid as err:
            return self.json_message(f"Key malformed: {err}", 400)

        opp = request.app["opp"]

        try:
            # We just validate, we don't store that data because
            # we don't want to store the defaults.
            if self.data_validator:
                await self.data_validator(opp, data)
            else:
                self.data_schema(data)
        except (vol.Invalid, OpenPeerPowerError) as err:
            return self.json_message(f"Message malformed: {err}", 400)

        path = opp.config.path(self.path)

        async with self.mutation_lock:
            current = await self.read_config(opp)
            self._write_value(opp, current, config_key, data)

            await opp.async_add_executor_job(_write, path, current)

        if self.post_write_hook is not None:
            opp.async_create_task(
                self.post_write_hook(ACTION_CREATE_UPDATE, config_key)
            )

        return self.json({"result": "ok"})

    async def delete(self, request, config_key):
        """Remove an entry."""
        opp = request.app["opp"]
        async with self.mutation_lock:
            current = await self.read_config(opp)
            value = self._get_value(opp, current, config_key)
            path = opp.config.path(self.path)

            if value is None:
                return self.json_message("Resource not found", 404)

            self._delete_value(opp, current, config_key)
            await opp.async_add_executor_job(_write, path, current)

        if self.post_write_hook is not None:
            opp.async_create_task(self.post_write_hook(ACTION_DELETE, config_key))

        return self.json({"result": "ok"})

    async def read_config(self, opp):
        """Read the config."""
        current = await opp.async_add_job(_read, opp.config.path(self.path))
        if not current:
            current = self._empty_config()
        return current


class EditKeyBasedConfigView(BaseEditConfigView):
    """Configure a list of entries."""

    def _empty_config(self):
        """Return an empty config."""
        return {}

    def _get_value(self, opp, data, config_key):
        """Get value."""
        return data.get(config_key)

    def _write_value(self, opp, data, config_key, new_value):
        """Set value."""
        data.setdefault(config_key, {}).update(new_value)

    def _delete_value(self, opp, data, config_key):
        """Delete value."""
        return data.pop(config_key)


class EditIdBasedConfigView(BaseEditConfigView):
    """Configure key based config entries."""

    def _empty_config(self):
        """Return an empty config."""
        return []

    def _get_value(self, opp, data, config_key):
        """Get value."""
        return next((val for val in data if val.get(CONF_ID) == config_key), None)

    def _write_value(self, opp, data, config_key, new_value):
        """Set value."""
        value = self._get_value(opp, data, config_key)

        if value is None:
            value = {CONF_ID: config_key}
            data.append(value)

        value.update(new_value)

    def _delete_value(self, opp, data, config_key):
        """Delete value."""
        index = next(
            idx for idx, val in enumerate(data) if val.get(CONF_ID) == config_key
        )
        data.pop(index)


def _read(path):
    """Read YAML helper."""
    if not os.path.isfile(path):
        return None

    return load_yaml(path)


def _write(path, data):
    """Write YAML helper."""
    # Do it before opening file. If dump causes error it will now not
    # truncate the file.
    data = dump(data)
    with open(path, "w", encoding="utf-8") as outfile:
        outfile.write(data)
