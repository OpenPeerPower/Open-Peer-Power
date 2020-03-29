"""Support for Opp.io."""
from datetime import timedelta
import logging
import os

import voluptuous as vol

from openpeerpower.auth.const import GROUP_ID_ADMIN
from openpeerpower.components.openpeerpower import SERVICE_CHECK_CONFIG
import openpeerpower.config as conf_util
from openpeerpower.const import (
    ATTR_NAME,
    EVENT_CORE_CONFIG_UPDATE,
    SERVICE_OPENPEERPOWER_RESTART,
    SERVICE_OPENPEERPOWER_STOP,
)
from openpeerpower.core import DOMAIN as OPP_DOMAIN, callback
from openpeerpower.exceptions import OpenPeerPowerError
import openpeerpower.helpers.config_validation as cv
from openpeerpower.loader import bind_opp
from openpeerpower.util.dt import utcnow

from .addon_panel import async_setup_addon_panel
from .auth import async_setup_auth_view
from .discovery import async_setup_discovery_view
from .handler import OppIO, OppioAPIError
from .http import OppIOView
from .ingress import async_setup_ingress_view

_LOGGER = logging.getLogger(__name__)

DOMAIN = "oppio"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

CONF_FRONTEND_REPO = "development_repo"

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.Schema({vol.Optional(CONF_FRONTEND_REPO): cv.isdir})},
    extra=vol.ALLOW_EXTRA,
)


DATA_OPENPEERPOWER_VERSION = "oppio_opp_version"
OPPIO_UPDATE_INTERVAL = timedelta(minutes=55)

SERVICE_ADDON_START = "addon_start"
SERVICE_ADDON_STOP = "addon_stop"
SERVICE_ADDON_RESTART = "addon_restart"
SERVICE_ADDON_STDIN = "addon_stdin"
SERVICE_HOST_SHUTDOWN = "host_shutdown"
SERVICE_HOST_REBOOT = "host_reboot"
SERVICE_SNAPSHOT_FULL = "snapshot_full"
SERVICE_SNAPSHOT_PARTIAL = "snapshot_partial"
SERVICE_RESTORE_FULL = "restore_full"
SERVICE_RESTORE_PARTIAL = "restore_partial"

ATTR_ADDON = "addon"
ATTR_INPUT = "input"
ATTR_SNAPSHOT = "snapshot"
ATTR_ADDONS = "addons"
ATTR_FOLDERS = "folders"
ATTR_OPENPEERPOWER = "openpeerpower"
ATTR_PASSWORD = "password"

SCHEMA_NO_DATA = vol.Schema({})

SCHEMA_ADDON = vol.Schema({vol.Required(ATTR_ADDON): cv.slug})

SCHEMA_ADDON_STDIN = SCHEMA_ADDON.extend(
    {vol.Required(ATTR_INPUT): vol.Any(dict, cv.string)}
)

SCHEMA_SNAPSHOT_FULL = vol.Schema(
    {vol.Optional(ATTR_NAME): cv.string, vol.Optional(ATTR_PASSWORD): cv.string}
)

SCHEMA_SNAPSHOT_PARTIAL = SCHEMA_SNAPSHOT_FULL.extend(
    {
        vol.Optional(ATTR_FOLDERS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ADDONS): vol.All(cv.ensure_list, [cv.string]),
    }
)

SCHEMA_RESTORE_FULL = vol.Schema(
    {vol.Required(ATTR_SNAPSHOT): cv.slug, vol.Optional(ATTR_PASSWORD): cv.string}
)

SCHEMA_RESTORE_PARTIAL = SCHEMA_RESTORE_FULL.extend(
    {
        vol.Optional(ATTR_OPENPEERPOWER): cv.boolean,
        vol.Optional(ATTR_FOLDERS): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ADDONS): vol.All(cv.ensure_list, [cv.string]),
    }
)

MAP_SERVICE_API = {
    SERVICE_ADDON_START: ("/addons/{addon}/start", SCHEMA_ADDON, 60, False),
    SERVICE_ADDON_STOP: ("/addons/{addon}/stop", SCHEMA_ADDON, 60, False),
    SERVICE_ADDON_RESTART: ("/addons/{addon}/restart", SCHEMA_ADDON, 60, False),
    SERVICE_ADDON_STDIN: ("/addons/{addon}/stdin", SCHEMA_ADDON_STDIN, 60, False),
    SERVICE_HOST_SHUTDOWN: ("/host/shutdown", SCHEMA_NO_DATA, 60, False),
    SERVICE_HOST_REBOOT: ("/host/reboot", SCHEMA_NO_DATA, 60, False),
    SERVICE_SNAPSHOT_FULL: ("/snapshots/new/full", SCHEMA_SNAPSHOT_FULL, 300, True),
    SERVICE_SNAPSHOT_PARTIAL: (
        "/snapshots/new/partial",
        SCHEMA_SNAPSHOT_PARTIAL,
        300,
        True,
    ),
    SERVICE_RESTORE_FULL: (
        "/snapshots/{snapshot}/restore/full",
        SCHEMA_RESTORE_FULL,
        300,
        True,
    ),
    SERVICE_RESTORE_PARTIAL: (
        "/snapshots/{snapshot}/restore/partial",
        SCHEMA_RESTORE_PARTIAL,
        300,
        True,
    ),
}


@callback
@bind_opp
def get_openpeerpower_version(opp):
    """Return latest available Open Peer Power version.

    Async friendly.
    """
    return opp.data.get(DATA_OPENPEERPOWER_VERSION)


@callback
@bind_opp
def is_oppio(opp):
    """Return true if Opp.io is loaded.

    Async friendly.
    """
    return DOMAIN in opp.config.components


async def async_setup(opp, config):
    """Set up the Opp.io component."""
    # Check local setup
    for env in ("OPPIO", "OPPIO_TOKEN"):
        if os.environ.get(env):
            continue
        _LOGGER.error("Missing %s environment variable.", env)
        return False

    host = os.environ["OPPIO"]
    websession = opp.helpers.aiohttp_client.async_get_clientsession()
    opp.data[DOMAIN] = oppio = OppIO(opp.loop, websession, host)

    if not await oppio.is_connected():
        _LOGGER.warning("Not connected with Opp.io / system to busy!")

    store = opp.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load()

    if data is None:
        data = {}

    refresh_token = None
    if "oppio_user" in data:
        user = await opp.auth.async_get_user(data["oppio_user"])
        if user and user.refresh_tokens:
            refresh_token = list(user.refresh_tokens.values())[0]

            # Migrate old Opp.io users to be admin.
            if not user.is_admin:
                await opp.auth.async_update_user(user, group_ids=[GROUP_ID_ADMIN])

    if refresh_token is None:
        user = await opp.auth.async_create_system_user("Opp.io", [GROUP_ID_ADMIN])
        refresh_token = await opp.auth.async_create_refresh_token(user)
        data["oppio_user"] = user.id
        await store.async_save(data)

    # This overrides the normal API call that would be forwarded
    development_repo = config.get(DOMAIN, {}).get(CONF_FRONTEND_REPO)
    if development_repo is not None:
        opp.http.register_static_path(
            "/api/oppio/app", os.path.join(development_repo, "oppio/build"), False
        )

    opp.http.register_view(OppIOView(host, websession))

    if "frontend" in opp.config.components:
        await opp.components.panel_custom.async_register_panel(
            frontend_url_path="oppio",
            webcomponent_name="oppio-main",
            sidebar_title="Supervisor",
            sidebar_icon="opp:open-peer-power",
            js_url="/api/oppio/app/entrypoint.js",
            embed_iframe=True,
            require_admin=True,
        )

    await oppio.update_opp_api(config.get("http", {}), refresh_token)

    async def push_config(_):
        """Push core config to Opp.io."""
        await oppio.update_opp_timezone(str(opp.config.time_zone))

    opp.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, push_config)

    await push_config(None)

    async def async_service_handler(service):
        """Handle service calls for Opp.io."""
        api_command = MAP_SERVICE_API[service.service][0]
        data = service.data.copy()
        addon = data.pop(ATTR_ADDON, None)
        snapshot = data.pop(ATTR_SNAPSHOT, None)
        payload = None

        # Pass data to Opp.io API
        if service.service == SERVICE_ADDON_STDIN:
            payload = data[ATTR_INPUT]
        elif MAP_SERVICE_API[service.service][3]:
            payload = data

        # Call API
        try:
            await oppio.send_command(
                api_command.format(addon=addon, snapshot=snapshot),
                payload=payload,
                timeout=MAP_SERVICE_API[service.service][2],
            )
        except OppioAPIError as err:
            _LOGGER.error("Error on Opp.io API: %s", err)

    for service, settings in MAP_SERVICE_API.items():
        opp.services.async_register(
            DOMAIN, service, async_service_handler, schema=settings[1]
        )

    async def update_openpeerpower_version(now):
        """Update last available Open Peer Power version."""
        try:
            data = await oppio.get_openpeerpower_info()
            opp.data[DATA_OPENPEERPOWER_VERSION] = data["last_version"]
        except OppioAPIError as err:
            _LOGGER.warning("Can't read last version: %s", err)

        opp.helpers.event.async_track_point_in_utc_time(
            update_openpeerpower_version, utcnow() + OPPIO_UPDATE_INTERVAL
        )

    # Fetch last version
    await update_openpeerpower_version(None)

    async def async_handle_core_service(call):
        """Service handler for handling core services."""
        if call.service == SERVICE_OPENPEERPOWER_STOP:
            await oppio.stop_openpeerpower()
            return

        try:
            errors = await conf_util.async_check_op_config_file(opp)
        except OpenPeerPowerError:
            return

        if errors:
            _LOGGER.error(errors)
            opp.components.persistent_notification.async_create(
                "Config error. See [the logs](/developer-tools/logs) for details.",
                "Config validating",
                f"{OPP_DOMAIN}.check_config",
            )
            return

        if call.service == SERVICE_OPENPEERPOWER_RESTART:
            await oppio.restart_openpeerpower()

    # Mock core services
    for service in (
        SERVICE_OPENPEERPOWER_STOP,
        SERVICE_OPENPEERPOWER_RESTART,
        SERVICE_CHECK_CONFIG,
    ):
        opp.services.async_register(OPP_DOMAIN, service, async_handle_core_service)

    # Init discovery Opp.io feature
    async_setup_discovery_view(opp, oppio)

    # Init auth Opp.io feature
    async_setup_auth_view(opp, user)

    # Init ingress Opp.io feature
    async_setup_ingress_view(opp, host)

    # Init add-on ingress panels
    await async_setup_addon_panel(opp, oppio)

    return True
