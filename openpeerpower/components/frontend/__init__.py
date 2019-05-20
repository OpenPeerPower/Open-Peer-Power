"""Handle the frontend for Open Peer Power."""
import asyncio
import json
import logging
import os
import pathlib

from aiohttp import web
import voluptuous as vol
import jinja2

import openpeerpower.helpers.config_validation as cv
from openpeerpower.components.http.view import OpenPeerPowerView
from openpeerpower.components import websocket_api
from openpeerpower.config import find_config_file, load_yaml_config_file
from openpeerpower.const import CONF_NAME, EVENT_THEMES_UPDATED
from openpeerpower.core import callback
from openpeerpower.helpers.translation import async_get_translations
from openpeerpower.loader import bind_opp

from .storage import async_setup_frontend_storage

DOMAIN = 'frontend'
CONF_THEMES = 'themes'
CONF_EXTRA_HTML_URL = 'extra_html_url'
CONF_EXTRA_HTML_URL_ES5 = 'extra_html_url_es5'
CONF_FRONTEND_REPO = 'development_repo'
CONF_JS_VERSION = 'javascript_version'

DEFAULT_THEME_COLOR = '#03A9F4'

MANIFEST_JSON = {
    'background_color': '#FFFFFF',
    'description':
    'Home automation platform that puts local control and privacy first.',
    'dir': 'ltr',
    'display': 'standalone',
    'icons': [],
    'lang': 'en-US',
    'name': 'Open Peer Power',
    'short_name': 'Assistant',
    'start_url': '/?homescreen=1',
    'theme_color': DEFAULT_THEME_COLOR
}

for size in (192, 384, 512, 1024):
    MANIFEST_JSON['icons'].append({
        'src': '/static/icons/favicon-{size}x{size}.png'.format(size=size),
        'sizes': '{size}x{size}'.format(size=size),
        'type': 'image/png'
    })

DATA_FINALIZE_PANEL = 'frontend_finalize_panel'
DATA_PANELS = 'frontend_panels'
DATA_JS_VERSION = 'frontend_js_version'
DATA_EXTRA_HTML_URL = 'frontend_extra_html_url'
DATA_EXTRA_HTML_URL_ES5 = 'frontend_extra_html_url_es5'
DATA_THEMES = 'frontend_themes'
DATA_DEFAULT_THEME = 'frontend_default_theme'
DEFAULT_THEME = 'default'

PRIMARY_COLOR = 'primary-color'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_FRONTEND_REPO): cv.isdir,
        vol.Optional(CONF_THEMES): vol.Schema({
            cv.string: {cv.string: cv.string}
        }),
        vol.Optional(CONF_EXTRA_HTML_URL):
            vol.All(cv.ensure_list, [cv.string]),
        # We no longer use these options.
        vol.Optional(CONF_EXTRA_HTML_URL_ES5): cv.match_all,
        vol.Optional(CONF_JS_VERSION):  cv.match_all,
    }),
}, extra=vol.ALLOW_EXTRA)

SERVICE_SET_THEME = 'set_theme'
SERVICE_RELOAD_THEMES = 'reload_themes'
SERVICE_SET_THEME_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
})
WS_TYPE_GET_PANELS = 'get_panels'
SCHEMA_GET_PANELS = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required('type'): WS_TYPE_GET_PANELS,
})
WS_TYPE_GET_THEMES = 'frontend/get_themes'
SCHEMA_GET_THEMES = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required('type'): WS_TYPE_GET_THEMES,
})
WS_TYPE_GET_TRANSLATIONS = 'frontend/get_translations'
SCHEMA_GET_TRANSLATIONS = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
    vol.Required('type'): WS_TYPE_GET_TRANSLATIONS,
    vol.Required('language'): str,
})


class Panel:
    """Abstract class for panels."""

    # Name of the webcomponent
    component_name = None

    # Icon to show in the sidebar (optional)
    sidebar_icon = None

    # Title to show in the sidebar (optional)
    sidebar_title = None

    # Url to show the panel in the frontend
    frontend_url_path = None

    # Config to pass to the webcomponent
    config = None

    # If the panel should only be visible to admins
    require_admin = False

    def __init__(self, component_name, sidebar_title, sidebar_icon,
                 frontend_url_path, config, require_admin):
        """Initialize a built-in panel."""
        self.component_name = component_name
        self.sidebar_title = sidebar_title
        self.sidebar_icon = sidebar_icon
        self.frontend_url_path = frontend_url_path or component_name
        self.config = config
        self.require_admin = require_admin

    @callback
    def async_register_index_routes(self, router, index_view):
        """Register routes for panel to be served by index view."""
        router.add_route(
            'get', '/{}'.format(self.frontend_url_path), index_view.get)
        router.add_route(
            'get', '/{}/{{extra:.+}}'.format(self.frontend_url_path),
            index_view.get)

    @callback
    def to_response(self):
        """Panel as dictionary."""
        return {
            'component_name': self.component_name,
            'icon': self.sidebar_icon,
            'title': self.sidebar_title,
            'config': self.config,
            'url_path': self.frontend_url_path,
            'require_admin': self.require_admin,
        }


@bind_opp
async def async_register_built_in_panel(opp, component_name,
                                        sidebar_title=None, sidebar_icon=None,
                                        frontend_url_path=None, config=None,
                                        require_admin=False):
    """Register a built-in panel."""
    panel = Panel(component_name, sidebar_title, sidebar_icon,
                  frontend_url_path, config, require_admin)

    panels = opp.data.get(DATA_PANELS)
    if panels is None:
        panels = opp.data[DATA_PANELS] = {}

    if panel.frontend_url_path in panels:
        _LOGGER.warning("Overwriting component %s", panel.frontend_url_path)

    if DATA_FINALIZE_PANEL in opp.data:
        opp.data[DATA_FINALIZE_PANEL](panel)

    panels[panel.frontend_url_path] = panel


@bind_opp
@callback
def add_extra_html_url(opp, url, es5=False):
    """Register extra html url to load."""
    key = DATA_EXTRA_HTML_URL_ES5 if es5 else DATA_EXTRA_HTML_URL
    url_set = opp.data.get(key)
    if url_set is None:
        url_set = opp.data[key] = set()
    url_set.add(url)


def add_manifest_json_key(key, val):
    """Add a keyval to the manifest.json."""
    MANIFEST_JSON[key] = val


def _frontend_root(dev_repo_path):
    """Return root path to the frontend files."""
    if dev_repo_path is not None:
        return pathlib.Path(dev_repo_path) / 'opp_frontend'

    import opp_frontend
    return opp_frontend.where()


async def async_setup(opp, config):
    """Set up the serving of the frontend."""
    await async_setup_frontend_storage(opp)
    opp.components.websocket_api.async_register_command(
        WS_TYPE_GET_PANELS, websocket_get_panels, SCHEMA_GET_PANELS)
    opp.components.websocket_api.async_register_command(
        WS_TYPE_GET_THEMES, websocket_get_themes, SCHEMA_GET_THEMES)
    opp.components.websocket_api.async_register_command(
        WS_TYPE_GET_TRANSLATIONS, websocket_get_translations,
        SCHEMA_GET_TRANSLATIONS)
    opp.http.register_view(ManifestJSONView)

    conf = config.get(DOMAIN, {})

    repo_path = conf.get(CONF_FRONTEND_REPO)
    is_dev = repo_path is not None
    root_path = _frontend_root(repo_path)

    for path, should_cache in (
            ("service_worker.js", False),
            ("robots.txt", False),
            ("onboarding.html", True),
            ("static", True),
            ("frontend_latest", True),
            ("frontend_es5", True),
    ):
        opp.http.register_static_path(
            "/{}".format(path), str(root_path / path), should_cache)

    opp.http.register_static_path(
        "/auth/authorize", str(root_path / "authorize.html"), False)

    local = opp.config.path('www')
    if os.path.isdir(local):
        opp.http.register_static_path("/local", local, not is_dev)

    index_view = IndexView(repo_path)
    opp.http.register_view(index_view)

    @callback
    def async_finalize_panel(panel):
        """Finalize setup of a panel."""
        panel.async_register_index_routes(opp.http.app.router, index_view)

    await asyncio.wait(
        [async_register_built_in_panel(opp, panel) for panel in (
            'kiosk', 'states', 'profile')], loop=opp.loop)
    await asyncio.wait(
        [async_register_built_in_panel(opp, panel, require_admin=True)
         for panel in ('dev-event', 'dev-info', 'dev-service', 'dev-state',
                       'dev-template', 'dev-mqtt')], loop=opp.loop)

    opp.data[DATA_FINALIZE_PANEL] = async_finalize_panel

    # Finalize registration of panels that registered before frontend was setup
    # This includes the built-in panels from line above.
    for panel in opp.data[DATA_PANELS].values():
        async_finalize_panel(panel)

    if DATA_EXTRA_HTML_URL not in opp.data:
        opp.data[DATA_EXTRA_HTML_URL] = set()

    for url in conf.get(CONF_EXTRA_HTML_URL, []):
        add_extra_html_url(opp, url, False)

    _async_setup_themes(opp, conf.get(CONF_THEMES))

    return True


@callback
def _async_setup_themes(opp, themes):
    """Set up themes data and services."""
    opp.data[DATA_DEFAULT_THEME] = DEFAULT_THEME
    if themes is None:
        opp.data[DATA_THEMES] = {}
        return

    opp.data[DATA_THEMES] = themes

    @callback
    def update_theme_and_fire_event():
        """Update theme_color in manifest."""
        name = opp.data[DATA_DEFAULT_THEME]
        themes = opp.data[DATA_THEMES]
        if name != DEFAULT_THEME and PRIMARY_COLOR in themes[name]:
            MANIFEST_JSON['theme_color'] = themes[name][PRIMARY_COLOR]
        else:
            MANIFEST_JSON['theme_color'] = DEFAULT_THEME_COLOR
        opp.bus.async_fire(EVENT_THEMES_UPDATED, {
            'themes': themes,
            'default_theme': name,
        })

    @callback
    def set_theme(call):
        """Set backend-preferred theme."""
        data = call.data
        name = data[CONF_NAME]
        if name == DEFAULT_THEME or name in opp.data[DATA_THEMES]:
            _LOGGER.info("Theme %s set as default", name)
            opp.data[DATA_DEFAULT_THEME] = name
            update_theme_and_fire_event()
        else:
            _LOGGER.warning("Theme %s is not defined.", name)

    @callback
    def reload_themes(_):
        """Reload themes."""
        path = find_config_file(opp.config.config_dir)
        new_themes = load_yaml_config_file(path)[DOMAIN].get(CONF_THEMES, {})
        opp.data[DATA_THEMES] = new_themes
        if opp.data[DATA_DEFAULT_THEME] not in new_themes:
            opp.data[DATA_DEFAULT_THEME] = DEFAULT_THEME
        update_theme_and_fire_event()

    opp.services.async_register(
        DOMAIN, SERVICE_SET_THEME, set_theme, schema=SERVICE_SET_THEME_SCHEMA)
    opp.services.async_register(DOMAIN, SERVICE_RELOAD_THEMES, reload_themes)


class IndexView(OpenPeerPowerView):
    """Serve the frontend."""

    url = '/'
    name = 'frontend:index'
    requires_auth = False

    def __init__(self, repo_path):
        """Initialize the frontend view."""
        self.repo_path = repo_path
        self._template_cache = None

    def get_template(self):
        """Get template."""
        tpl = self._template_cache
        if tpl is None:
            with open(
                    str(_frontend_root(self.repo_path) / 'index.html')
            ) as file:
                tpl = jinja2.Template(file.read())

            # Cache template if not running from repository
            if self.repo_path is None:
                self._template_cache = tpl

        return tpl

    async def get(self, request, extra=None):
        """Serve the index view."""
        opp = request.app['opp']

        if not opp.components.onboarding.async_is_onboarded():
            return web.Response(status=302, headers={
                'location': '/onboarding.html'
            })

        template = self._template_cache

        if template is None:
            template = await opp.async_add_executor_job(self.get_template)

        return web.Response(
            text=template.render(
                theme_color=MANIFEST_JSON['theme_color'],
                extra_urls=opp.data[DATA_EXTRA_HTML_URL],
            ),
            content_type='text/html'
        )


class ManifestJSONView(OpenPeerPowerView):
    """View to return a manifest.json."""

    requires_auth = False
    url = '/manifest.json'
    name = 'manifestjson'

    @callback
    def get(self, request):    # pylint: disable=no-self-use
        """Return the manifest.json."""
        msg = json.dumps(MANIFEST_JSON, sort_keys=True)
        return web.Response(text=msg, content_type="application/manifest+json")


@callback
def websocket_get_panels(opp, connection, msg):
    """Handle get panels command.

    Async friendly.
    """
    user_is_admin = connection.user.is_admin
    panels = {
        panel_key: panel.to_response()
        for panel_key, panel in connection.opp.data[DATA_PANELS].items()
        if user_is_admin or not panel.require_admin}

    connection.send_message(websocket_api.result_message(
        msg['id'], panels))


@callback
def websocket_get_themes(opp, connection, msg):
    """Handle get themes command.

    Async friendly.
    """
    connection.send_message(websocket_api.result_message(msg['id'], {
        'themes': opp.data[DATA_THEMES],
        'default_theme': opp.data[DATA_DEFAULT_THEME],
    }))


@websocket_api.async_response
async def websocket_get_translations(opp, connection, msg):
    """Handle get translations command.

    Async friendly.
    """
    resources = await async_get_translations(opp, msg['language'])
    connection.send_message(websocket_api.result_message(
        msg['id'], {
            'resources': resources,
        }
    ))
