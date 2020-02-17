"""Websocket API for mobile_app."""
import voluptuous as vol

from openpeerpower.components.websocket_api import (
    ActiveConnection,
    async_register_command,
    async_response,
    error_message,
    result_message,
    websocket_command,
    ws_require_user,
)
from openpeerpower.components.websocket_api.const import (
    ERR_INVALID_FORMAT,
    ERR_NOT_FOUND,
    ERR_UNAUTHORIZED,
)
from openpeerpower.const import CONF_WEBHOOK_ID
from openpeerpower.exceptions import OpenPeerPowerError
from openpeerpower.helpers import config_validation as cv
from openpeerpower.helpers.typing import OpenPeerPowerType

from .const import (
    CONF_CLOUDHOOK_URL,
    CONF_USER_ID,
    DATA_CONFIG_ENTRIES,
    DATA_DELETED_IDS,
    DATA_STORE,
    DOMAIN,
)
from .helpers import safe_registration, savable_state


def register_websocket_handlers(opp: OpenPeerPowerType) -> bool:
    """Register the websocket handlers."""
    async_register_command(opp, websocket_get_user_registrations)

    async_register_command(opp, websocket_delete_registration)

    return True


@ws_require_user()
@async_response
@websocket_command(
    {
        vol.Required("type"): "mobile_app/get_user_registrations",
        vol.Optional(CONF_USER_ID): cv.string,
    }
)
async def websocket_get_user_registrations(
    opp: OpenPeerPowerType, connection: ActiveConnection, msg: dict
) -> None:
    """Return all registrations or just registrations for given user ID."""
    user_id = msg.get(CONF_USER_ID, connection.user.id)

    if user_id != connection.user.id and not connection.user.is_admin:
        # If user ID is provided and is not current user ID and current user
        # isn't an admin user
        connection.send_error(msg["id"], ERR_UNAUTHORIZED, "Unauthorized")
        return

    user_registrations = []

    for config_entry in opp.config_entries.async_entries(domain=DOMAIN):
        registration = config_entry.data
        if connection.user.is_admin or registration[CONF_USER_ID] is user_id:
            user_registrations.append(safe_registration(registration))

    connection.send_message(result_message(msg["id"], user_registrations))


@ws_require_user()
@async_response
@websocket_command(
    {
        vol.Required("type"): "mobile_app/delete_registration",
        vol.Required(CONF_WEBHOOK_ID): cv.string,
    }
)
async def websocket_delete_registration(
    opp: OpenPeerPowerType, connection: ActiveConnection, msg: dict
) -> None:
    """Delete the registration for the given webhook_id."""
    user = connection.user

    webhook_id = msg.get(CONF_WEBHOOK_ID)
    if webhook_id is None:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, "Webhook ID not provided")
        return

    config_entry = opp.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]

    registration = config_entry.data

    if registration is None:
        connection.send_error(
            msg["id"], ERR_NOT_FOUND, "Webhook ID not found in storage"
        )
        return

    if registration[CONF_USER_ID] != user.id and not user.is_admin:
        return error_message(
            msg["id"], ERR_UNAUTHORIZED, "User is not registration owner"
        )

    await opp.config_entries.async_remove(config_entry.entry_id)

    opp.data[DOMAIN][DATA_DELETED_IDS].append(webhook_id)

    store = opp.data[DOMAIN][DATA_STORE]

    try:
        await store.async_save(savable_state(opp))
    except OpenPeerPowerError:
        return error_message(msg["id"], "internal_error", "Error deleting registration")

    if CONF_CLOUDHOOK_URL in registration:
        await opp.components.cloud.async_delete_cloudhook(webhook_id)

    connection.send_message(result_message(msg["id"], "ok"))
