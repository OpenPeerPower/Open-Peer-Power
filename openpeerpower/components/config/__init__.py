"""Component to configure Open Peer Power via an API."""
import asyncio
import importlib
import os

import voluptuous as vol

from openpeerpower.core import callback
from openpeerpower.const import EVENT_COMPONENT_LOADED, CONF_ID
from openpeerpower.setup import ATTR_COMPONENT
from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.util.yaml import load_yaml, dump

DOMAIN = 'config'
SECTIONS = (
    'area_registry',
    'auth',
    'auth_provider_openpeerpower',
    'automation',
    'config_entries',
    'core',
    'customize',
    'device_registry',
    'entity_registry',
    'group',
    'script',
)
ON_DEMAND = ('zwave',)


async def async_setup(opp, config):
    """Set up the config component."""
    await opp.components.frontend.async_register_built_in_panel(
        'config', 'config', 'opp:settings', require_admin=True)

    async def setup_panel(panel_name):
        """Set up a panel."""
        panel = importlib.import_module('.{}'.format(panel_name), __name__)

        if not panel:
            return

        success = await panel.async_setup(opp)

        if success:
            key = '{}.{}'.format(DOMAIN, panel_name)
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
        await asyncio.wait(tasks, loop=opp.loop)

    return True


class BaseEditConfigView(OpenPeerPowerView):
    """Configure a Group endpoint."""

    def __init__(self, component, config_type, path, key_schema, data_schema,
                 *, post_write_hook=None):
        """Initialize a config view."""
        self.url = '/api/config/%s/%s/{config_key}' % (component, config_type)
        self.name = 'api:config:%s:%s' % (component, config_type)
        self.path = path
        self.key_schema = key_schema
        self.data_schema = data_schema
        self.post_write_hook = post_write_hook

    def _empty_config(self):
        """Empty config if file not found."""
        raise NotImplementedError

    def _get_value(self, opp, data, config_key):
        """Get value."""
        raise NotImplementedError

    def _write_value(self, opp, data, config_key, new_value):
        """Set value."""
        raise NotImplementedError

    async def get(self, request, config_key):
        """Fetch device specific config."""
        opp = request.app['opp']
        current = await self.read_config(opp)
        value = self._get_value(opp, current, config_key)

        if value is None:
            return self.json_message('Resource not found', 404)

        return self.json(value)

    async def post(self, request, config_key):
        """Validate config and return results."""
        try:
            data = await request.json()
        except ValueError:
            return self.json_message('Invalid JSON specified', 400)

        try:
            self.key_schema(config_key)
        except vol.Invalid as err:
            return self.json_message('Key malformed: {}'.format(err), 400)

        try:
            # We just validate, we don't store that data because
            # we don't want to store the defaults.
            self.data_schema(data)
        except vol.Invalid as err:
            return self.json_message('Message malformed: {}'.format(err), 400)

        opp = request.app['opp']
        path = opp.config.path(self.path)

        current = await self.read_config(opp)
        self._write_value(opp, current, config_key, data)

        await opp.async_add_job(_write, path, current)

        if self.post_write_hook is not None:
            opp.async_create_task(self.post_write_hook(opp))

        return self.json({
            'result': 'ok',
        })

    async def read_config(self, opp):
        """Read the config."""
        current = await opp.async_add_job(
            _read, opp.config.path(self.path))
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


class EditIdBasedConfigView(BaseEditConfigView):
    """Configure key based config entries."""

    def _empty_config(self):
        """Return an empty config."""
        return []

    def _get_value(self, opp, data, config_key):
        """Get value."""
        return next(
            (val for val in data if val.get(CONF_ID) == config_key), None)

    def _write_value(self, opp, data, config_key, new_value):
        """Set value."""
        value = self._get_value(opp, data, config_key)

        if value is None:
            value = {CONF_ID: config_key}
            data.append(value)

        value.update(new_value)


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
    with open(path, 'w', encoding='utf-8') as outfile:
        outfile.write(data)
