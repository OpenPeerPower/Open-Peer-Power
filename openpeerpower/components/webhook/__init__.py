"""Webhooks for Open Peer Power."""
import logging
import secrets

from aiohttp.web import Request, Response
import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.components.http.view import OpenPeerPowerView
from openpeerpower.core import callback
from openpeerpower.loader import bind_opp

_LOGGER = logging.getLogger(__name__)

DOMAIN = "webhook"

URL_WEBHOOK_PATH = "/api/webhook/{webhook_id}"

WS_TYPE_LIST = "webhook/list"

SCHEMA_WS_LIST = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_LIST}
)


@callback
@bind_opp
def async_register(opp, domain, name, webhook_id, handler):
    """Register a webhook."""
    handlers = opp.data.setdefault(DOMAIN, {})

    if webhook_id in handlers:
        raise ValueError("Handler is already defined!")

    handlers[webhook_id] = {"domain": domain, "name": name, "handler": handler}


@callback
@bind_opp
def async_unregister(opp, webhook_id):
    """Remove a webhook."""
    handlers = opp.data.setdefault(DOMAIN, {})
    handlers.pop(webhook_id, None)


@callback
def async_generate_id():
    """Generate a webhook_id."""
    return secrets.token_hex(32)


@callback
@bind_opp
def async_generate_url(opp, webhook_id):
    """Generate the full URL for a webhook_id."""
    return "{}{}".format(opp.config.api.base_url, async_generate_path(webhook_id))


@callback
def async_generate_path(webhook_id):
    """Generate the path component for a webhook_id."""
    return URL_WEBHOOK_PATH.format(webhook_id=webhook_id)


@bind_opp
async def async_handle_webhook(opp, webhook_id, request):
    """Handle a webhook."""
    handlers = opp.data.setdefault(DOMAIN, {})
    webhook = handlers.get(webhook_id)

    # Always respond successfully to not give away if a hook exists or not.
    if webhook is None:
        _LOGGER.warning("Received message for unregistered webhook %s", webhook_id)
        return Response(status=200)

    try:
        response = await webhook["handler"](opp, webhook_id, request)
        if response is None:
            response = Response(status=200)
        return response
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Error processing webhook %s", webhook_id)
        return Response(status=200)


async def async_setup(opp, config):
    """Initialize the webhook component."""
    opp.http.register_view(WebhookView)
    opp.components.websocket_api.async_register_command(
        WS_TYPE_LIST, websocket_list, SCHEMA_WS_LIST
    )
    return True


class WebhookView(OpenPeerPowerView):
    """Handle incoming webhook requests."""

    url = URL_WEBHOOK_PATH
    name = "api:webhook"
    requires_auth = False
    cors_allowed = True

    async def _handle(self, request: Request, webhook_id):
        """Handle webhook call."""
        _LOGGER.debug("Handling webhook %s payload for %s", request.method, webhook_id)
        opp = request.app["opp"]
        return await async_handle_webhook(opp, webhook_id, request)

    head = _handle
    post = _handle
    put = _handle


@callback
def websocket_list(opp, connection, msg):
    """Return a list of webhooks."""
    handlers = opp.data.setdefault(DOMAIN, {})
    result = [
        {"webhook_id": webhook_id, "domain": info["domain"], "name": info["name"]}
        for webhook_id, info in handlers.items()
    ]

    connection.send_message(websocket_api.result_message(msg["id"], result))
