"""The HTTP api to control the cloud integration."""
import asyncio
from functools import wraps
import logging

import aiohttp
import async_timeout
import attr
from opp_cloud import Cloud, auth, thingtalk
from opp_cloud.const import STATE_DISCONNECTED
import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.components.alexa import (
    entities as alexa_entities,
    errors as alexa_errors,
)
from openpeerpower.components.google_assistant import helpers as google_helpers
from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.components.http.data_validator import RequestDataValidator
from openpeerpower.components.websocket_api import const as ws_const
from openpeerpower.core import callback

from .const import (
    DOMAIN,
    PREF_ALEXA_REPORT_STATE,
    PREF_ENABLE_ALEXA,
    PREF_ENABLE_GOOGLE,
    PREF_GOOGLE_REPORT_STATE,
    PREF_GOOGLE_SECURE_DEVICES_PIN,
    REQUEST_TIMEOUT,
    InvalidTrustedNetworks,
    InvalidTrustedProxies,
    RequireRelink,
)

_LOGGER = logging.getLogger(__name__)


WS_TYPE_STATUS = "cloud/status"
SCHEMA_WS_STATUS = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_STATUS}
)


WS_TYPE_SUBSCRIPTION = "cloud/subscription"
SCHEMA_WS_SUBSCRIPTION = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_SUBSCRIPTION}
)


WS_TYPE_HOOK_CREATE = "cloud/cloudhook/create"
SCHEMA_WS_HOOK_CREATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_HOOK_CREATE, vol.Required("webhook_id"): str}
)


WS_TYPE_HOOK_DELETE = "cloud/cloudhook/delete"
SCHEMA_WS_HOOK_DELETE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_HOOK_DELETE, vol.Required("webhook_id"): str}
)


_CLOUD_ERRORS = {
    InvalidTrustedNetworks: (
        500,
        "Remote UI not compatible with 127.0.0.1/::1 as a trusted network.",
    ),
    InvalidTrustedProxies: (
        500,
        "Remote UI not compatible with 127.0.0.1/::1 as trusted proxies.",
    ),
}


async def async_setup(opp):
    """Initialize the HTTP API."""
    async_register_command = opp.components.websocket_api.async_register_command
    async_register_command(WS_TYPE_STATUS, websocket_cloud_status, SCHEMA_WS_STATUS)
    async_register_command(
        WS_TYPE_SUBSCRIPTION, websocket_subscription, SCHEMA_WS_SUBSCRIPTION
    )
    async_register_command(websocket_update_prefs)
    async_register_command(
        WS_TYPE_HOOK_CREATE, websocket_hook_create, SCHEMA_WS_HOOK_CREATE
    )
    async_register_command(
        WS_TYPE_HOOK_DELETE, websocket_hook_delete, SCHEMA_WS_HOOK_DELETE
    )
    async_register_command(websocket_remote_connect)
    async_register_command(websocket_remote_disconnect)

    async_register_command(google_assistant_list)
    async_register_command(google_assistant_update)

    async_register_command(alexa_list)
    async_register_command(alexa_update)
    async_register_command(alexa_sync)

    async_register_command(thingtalk_convert)

    opp.http.register_view(GoogleActionsSyncView)
    opp.http.register_view(CloudLoginView)
    opp.http.register_view(CloudLogoutView)
    opp.http.register_view(CloudRegisterView)
    opp.http.register_view(CloudResendConfirmView)
    opp.http.register_view(CloudForgotPasswordView)

    _CLOUD_ERRORS.update(
        {
            auth.UserNotFound: (400, "User does not exist."),
            auth.UserNotConfirmed: (400, "Email not confirmed."),
            auth.UserExists: (400, "An account with the given email already exists."),
            auth.Unauthenticated: (401, "Authentication failed."),
            auth.PasswordChangeRequired: (400, "Password change required."),
            asyncio.TimeoutError: (502, "Unable to reach the Open Peer Power cloud."),
            aiohttp.ClientError: (500, "Error making internal request"),
        }
    )


def _handle_cloud_errors(handler):
    """Webview decorator to handle auth errors."""

    @wraps(handler)
    async def error_handler(view, request, *args, **kwargs):
        """Handle exceptions that raise from the wrapped request handler."""
        try:
            result = await handler(view, request, *args, **kwargs)
            return result

        except Exception as err:  # pylint: disable=broad-except
            status, msg = _process_cloud_exception(err, request.path)
            return view.json_message(
                msg, status_code=status, message_code=err.__class__.__name__.lower()
            )

    return error_handler


def _ws_handle_cloud_errors(handler):
    """Websocket decorator to handle auth errors."""

    @wraps(handler)
    async def error_handler(opp, connection, msg):
        """Handle exceptions that raise from the wrapped handler."""
        try:
            return await handler(opp, connection, msg)

        except Exception as err:  # pylint: disable=broad-except
            err_status, err_msg = _process_cloud_exception(err, msg["type"])
            connection.send_error(msg["id"], err_status, err_msg)

    return error_handler


def _process_cloud_exception(exc, where):
    """Process a cloud exception."""
    err_info = _CLOUD_ERRORS.get(exc.__class__)
    if err_info is None:
        _LOGGER.exception("Unexpected error processing request for %s", where)
        err_info = (502, f"Unexpected error: {exc}")
    return err_info


class GoogleActionsSyncView(OpenPeerPowerView):
    """Trigger a Google Actions Smart Home Sync."""

    url = "/api/cloud/google_actions/sync"
    name = "api:cloud:google_actions/sync"

    @_handle_cloud_errors
    async def post(self, request):
        """Trigger a Google Actions sync."""
        opp = request.app["opp"]
        cloud: Cloud = opp.data[DOMAIN]
        gconf = await cloud.client.get_google_config()
        status = await gconf.async_sync_entities(gconf.agent_user_id)
        return self.json({}, status_code=status)


class CloudLoginView(OpenPeerPowerView):
    """Login to Open Peer Power cloud."""

    url = "/api/cloud/login"
    name = "api:cloud:login"

    @_handle_cloud_errors
    @RequestDataValidator(
        vol.Schema({vol.Required("email"): str, vol.Required("password"): str})
    )
    async def post(self, request, data):
        """Handle login request."""
        opp = request.app["opp"]
        cloud = opp.data[DOMAIN]
        await cloud.login(data["email"], data["password"])
        return self.json({"success": True})


class CloudLogoutView(OpenPeerPowerView):
    """Log out of the Open Peer Power cloud."""

    url = "/api/cloud/logout"
    name = "api:cloud:logout"

    @_handle_cloud_errors
    async def post(self, request):
        """Handle logout request."""
        opp = request.app["opp"]
        cloud = opp.data[DOMAIN]

        with async_timeout.timeout(REQUEST_TIMEOUT):
            await cloud.logout()

        return self.json_message("ok")


class CloudRegisterView(OpenPeerPowerView):
    """Register on the Open Peer Power cloud."""

    url = "/api/cloud/register"
    name = "api:cloud:register"

    @_handle_cloud_errors
    @RequestDataValidator(
        vol.Schema(
            {
                vol.Required("email"): str,
                vol.Required("password"): vol.All(str, vol.Length(min=6)),
            }
        )
    )
    async def post(self, request, data):
        """Handle registration request."""
        opp = request.app["opp"]
        cloud = opp.data[DOMAIN]

        with async_timeout.timeout(REQUEST_TIMEOUT):
            await opp.async_add_job(
                cloud.auth.register, data["email"], data["password"]
            )

        return self.json_message("ok")


class CloudResendConfirmView(OpenPeerPowerView):
    """Resend email confirmation code."""

    url = "/api/cloud/resend_confirm"
    name = "api:cloud:resend_confirm"

    @_handle_cloud_errors
    @RequestDataValidator(vol.Schema({vol.Required("email"): str}))
    async def post(self, request, data):
        """Handle resending confirm email code request."""
        opp = request.app["opp"]
        cloud = opp.data[DOMAIN]

        with async_timeout.timeout(REQUEST_TIMEOUT):
            await opp.async_add_job(cloud.auth.resend_email_confirm, data["email"])

        return self.json_message("ok")


class CloudForgotPasswordView(OpenPeerPowerView):
    """View to start Forgot Password flow.."""

    url = "/api/cloud/forgot_password"
    name = "api:cloud:forgot_password"

    @_handle_cloud_errors
    @RequestDataValidator(vol.Schema({vol.Required("email"): str}))
    async def post(self, request, data):
        """Handle forgot password request."""
        opp = request.app["opp"]
        cloud = opp.data[DOMAIN]

        with async_timeout.timeout(REQUEST_TIMEOUT):
            await opp.async_add_job(cloud.auth.forgot_password, data["email"])

        return self.json_message("ok")


@callback
def websocket_cloud_status(opp, connection, msg):
    """Handle request for account info.

    Async friendly.
    """
    cloud = opp.data[DOMAIN]
    connection.send_message(
        websocket_api.result_message(msg["id"], _account_data(cloud))
    )


def _require_cloud_login(handler):
    """Websocket decorator that requires cloud to be logged in."""

    @wraps(handler)
    def with_cloud_auth(opp, connection, msg):
        """Require to be logged into the cloud."""
        cloud = opp.data[DOMAIN]
        if not cloud.is_logged_in:
            connection.send_message(
                websocket_api.error_message(
                    msg["id"], "not_logged_in", "You need to be logged in to the cloud."
                )
            )
            return

        handler(opp, connection, msg)

    return with_cloud_auth


@_require_cloud_login
@websocket_api.async_response
async def websocket_subscription(opp, connection, msg):
    """Handle request for account info."""

    cloud = opp.data[DOMAIN]

    with async_timeout.timeout(REQUEST_TIMEOUT):
        response = await cloud.fetch_subscription_info()

    if response.status != 200:
        connection.send_message(
            websocket_api.error_message(
                msg["id"], "request_failed", "Failed to request subscription"
            )
        )

    data = await response.json()

    # Check if a user is subscribed but local info is outdated
    # In that case, let's refresh and reconnect
    if data.get("provider") and not cloud.is_connected:
        _LOGGER.debug("Found disconnected account with valid subscriotion, connecting")
        await opp.async_add_executor_job(cloud.auth.renew_access_token)

        # Cancel reconnect in progress
        if cloud.iot.state != STATE_DISCONNECTED:
            await cloud.iot.disconnect()

        opp.async_create_task(cloud.iot.connect())

    connection.send_message(websocket_api.result_message(msg["id"], data))


@_require_cloud_login
@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "cloud/update_prefs",
        vol.Optional(PREF_ENABLE_GOOGLE): bool,
        vol.Optional(PREF_ENABLE_ALEXA): bool,
        vol.Optional(PREF_ALEXA_REPORT_STATE): bool,
        vol.Optional(PREF_GOOGLE_REPORT_STATE): bool,
        vol.Optional(PREF_GOOGLE_SECURE_DEVICES_PIN): vol.Any(None, str),
    }
)
async def websocket_update_prefs(opp, connection, msg):
    """Handle request for account info."""
    cloud = opp.data[DOMAIN]

    changes = dict(msg)
    changes.pop("id")
    changes.pop("type")

    # If we turn alexa linking on, validate that we can fetch access token
    if changes.get(PREF_ALEXA_REPORT_STATE):
        try:
            with async_timeout.timeout(10):
                await cloud.client.alexa_config.async_get_access_token()
        except asyncio.TimeoutError:
            connection.send_error(
                msg["id"], "alexa_timeout", "Timeout validating Alexa access token."
            )
            return
        except (alexa_errors.NoTokenAvailable, RequireRelink):
            connection.send_error(
                msg["id"],
                "alexa_relink",
                "Please go to the Alexa app and re-link the Open Peer Power "
                "skill and then try to enable state reporting.",
            )
            return

    await cloud.client.prefs.async_update(**changes)

    connection.send_message(websocket_api.result_message(msg["id"]))


@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
async def websocket_hook_create(opp, connection, msg):
    """Handle request for account info."""
    cloud = opp.data[DOMAIN]
    hook = await cloud.cloudhooks.async_create(msg["webhook_id"], False)
    connection.send_message(websocket_api.result_message(msg["id"], hook))


@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
async def websocket_hook_delete(opp, connection, msg):
    """Handle request for account info."""
    cloud = opp.data[DOMAIN]
    await cloud.cloudhooks.async_delete(msg["webhook_id"])
    connection.send_message(websocket_api.result_message(msg["id"]))


def _account_data(cloud):
    """Generate the auth data JSON response."""

    if not cloud.is_logged_in:
        return {"logged_in": False, "cloud": STATE_DISCONNECTED}

    claims = cloud.claims
    client = cloud.client
    remote = cloud.remote

    # Load remote certificate
    if remote.certificate:
        certificate = attr.asdict(remote.certificate)
    else:
        certificate = None

    return {
        "logged_in": True,
        "email": claims["email"],
        "cloud": cloud.iot.state,
        "prefs": client.prefs.as_dict(),
        "google_entities": client.google_user_config["filter"].config,
        "alexa_entities": client.alexa_user_config["filter"].config,
        "remote_domain": remote.instance_domain,
        "remote_connected": remote.is_connected,
        "remote_certificate": certificate,
    }


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
@websocket_api.websocket_command({"type": "cloud/remote/connect"})
async def websocket_remote_connect(opp, connection, msg):
    """Handle request for connect remote."""
    cloud = opp.data[DOMAIN]
    await cloud.client.prefs.async_update(remote_enabled=True)
    await cloud.remote.connect()
    connection.send_result(msg["id"], _account_data(cloud))


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
@websocket_api.websocket_command({"type": "cloud/remote/disconnect"})
async def websocket_remote_disconnect(opp, connection, msg):
    """Handle request for disconnect remote."""
    cloud = opp.data[DOMAIN]
    await cloud.client.prefs.async_update(remote_enabled=False)
    await cloud.remote.disconnect()
    connection.send_result(msg["id"], _account_data(cloud))


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
@websocket_api.websocket_command({"type": "cloud/google_assistant/entities"})
async def google_assistant_list(opp, connection, msg):
    """List all google assistant entities."""
    cloud = opp.data[DOMAIN]
    gconf = await cloud.client.get_google_config()
    entities = google_helpers.async_get_entities(opp, gconf)

    result = []

    for entity in entities:
        result.append(
            {
                "entity_id": entity.entity_id,
                "traits": [trait.name for trait in entity.traits()],
                "might_2fa": entity.might_2fa(),
            }
        )

    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
@websocket_api.websocket_command(
    {
        "type": "cloud/google_assistant/entities/update",
        "entity_id": str,
        vol.Optional("should_expose"): bool,
        vol.Optional("override_name"): str,
        vol.Optional("aliases"): [str],
        vol.Optional("disable_2fa"): bool,
    }
)
async def google_assistant_update(opp, connection, msg):
    """Update google assistant config."""
    cloud = opp.data[DOMAIN]
    changes = dict(msg)
    changes.pop("type")
    changes.pop("id")

    await cloud.client.prefs.async_update_google_entity_config(**changes)

    connection.send_result(
        msg["id"], cloud.client.prefs.google_entity_configs.get(msg["entity_id"])
    )


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
@websocket_api.websocket_command({"type": "cloud/alexa/entities"})
async def alexa_list(opp, connection, msg):
    """List all alexa entities."""
    cloud = opp.data[DOMAIN]
    entities = alexa_entities.async_get_entities(opp, cloud.client.alexa_config)

    result = []

    for entity in entities:
        result.append(
            {
                "entity_id": entity.entity_id,
                "display_categories": entity.default_display_categories(),
                "interfaces": [ifc.name() for ifc in entity.interfaces()],
            }
        )

    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@_ws_handle_cloud_errors
@websocket_api.websocket_command(
    {
        "type": "cloud/alexa/entities/update",
        "entity_id": str,
        vol.Optional("should_expose"): bool,
    }
)
async def alexa_update(opp, connection, msg):
    """Update alexa entity config."""
    cloud = opp.data[DOMAIN]
    changes = dict(msg)
    changes.pop("type")
    changes.pop("id")

    await cloud.client.prefs.async_update_alexa_entity_config(**changes)

    connection.send_result(
        msg["id"], cloud.client.prefs.alexa_entity_configs.get(msg["entity_id"])
    )


@websocket_api.require_admin
@_require_cloud_login
@websocket_api.async_response
@websocket_api.websocket_command({"type": "cloud/alexa/sync"})
async def alexa_sync(opp, connection, msg):
    """Sync with Alexa."""
    cloud = opp.data[DOMAIN]

    with async_timeout.timeout(10):
        try:
            success = await cloud.client.alexa_config.async_sync_entities()
        except alexa_errors.NoTokenAvailable:
            connection.send_error(
                msg["id"],
                "alexa_relink",
                "Please go to the Alexa app and re-link the Open Peer Power skill.",
            )
            return

    if success:
        connection.send_result(msg["id"])
    else:
        connection.send_error(msg["id"], ws_const.ERR_UNKNOWN_ERROR, "Unknown error")


@websocket_api.async_response
@websocket_api.websocket_command({"type": "cloud/thingtalk/convert", "query": str})
async def thingtalk_convert(opp, connection, msg):
    """Convert a query."""
    cloud = opp.data[DOMAIN]

    with async_timeout.timeout(10):
        try:
            connection.send_result(
                msg["id"], await thingtalk.async_convert(cloud, msg["query"])
            )
        except thingtalk.ThingTalkConversionError as err:
            connection.send_error(msg["id"], ws_const.ERR_UNKNOWN_ERROR, str(err))
