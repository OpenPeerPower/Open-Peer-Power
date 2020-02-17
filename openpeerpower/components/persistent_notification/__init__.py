"""Support for displaying persistent notifications."""
from collections import OrderedDict
import logging
from typing import Any, Mapping, MutableMapping, Optional

import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.core import OpenPeerPower, callback
from openpeerpower.exceptions import TemplateError
from openpeerpower.helpers import config_validation as cv
from openpeerpower.helpers.entity import async_generate_entity_id
from openpeerpower.loader import bind_opp
from openpeerpower.util import slugify
import openpeerpower.util.dt as dt_util

# mypy: allow-untyped-calls, allow-untyped-defs

ATTR_CREATED_AT = "created_at"
ATTR_MESSAGE = "message"
ATTR_NOTIFICATION_ID = "notification_id"
ATTR_TITLE = "title"
ATTR_STATUS = "status"

DOMAIN = "persistent_notification"

ENTITY_ID_FORMAT = DOMAIN + ".{}"

EVENT_PERSISTENT_NOTIFICATIONS_UPDATED = "persistent_notifications_updated"

SERVICE_CREATE = "create"
SERVICE_DISMISS = "dismiss"
SERVICE_MARK_READ = "mark_read"

SCHEMA_SERVICE_CREATE = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.template,
        vol.Optional(ATTR_TITLE): cv.template,
        vol.Optional(ATTR_NOTIFICATION_ID): cv.string,
    }
)

SCHEMA_SERVICE_DISMISS = vol.Schema({vol.Required(ATTR_NOTIFICATION_ID): cv.string})

SCHEMA_SERVICE_MARK_READ = vol.Schema({vol.Required(ATTR_NOTIFICATION_ID): cv.string})

DEFAULT_OBJECT_ID = "notification"
_LOGGER = logging.getLogger(__name__)

STATE = "notifying"
STATUS_UNREAD = "unread"
STATUS_READ = "read"


@bind_opp
def create(opp, message, title=None, notification_id=None):
    """Generate a notification."""
    opp.add_job(async_create, opp, message, title, notification_id)


@bind_opp
def dismiss(opp, notification_id):
    """Remove a notification."""
    opp.add_job(async_dismiss, opp, notification_id)


@callback
@bind_opp
def async_create(
    opp: OpenPeerPower,
    message: str,
    title: Optional[str] = None,
    notification_id: Optional[str] = None,
) -> None:
    """Generate a notification."""
    data = {
        key: value
        for key, value in [
            (ATTR_TITLE, title),
            (ATTR_MESSAGE, message),
            (ATTR_NOTIFICATION_ID, notification_id),
        ]
        if value is not None
    }

    opp.async_create_task(opp.services.async_call(DOMAIN, SERVICE_CREATE, data))


@callback
@bind_opp
def async_dismiss(opp: OpenPeerPower, notification_id: str) -> None:
    """Remove a notification."""
    data = {ATTR_NOTIFICATION_ID: notification_id}

    opp.async_create_task(opp.services.async_call(DOMAIN, SERVICE_DISMISS, data))


async def async_setup(opp: OpenPeerPower, config: dict) -> bool:
    """Set up the persistent notification component."""
    persistent_notifications: MutableMapping[str, MutableMapping] = OrderedDict()
    opp.data[DOMAIN] = {"notifications": persistent_notifications}

    @callback
    def create_service(call):
        """Handle a create notification service call."""
        title = call.data.get(ATTR_TITLE)
        message = call.data.get(ATTR_MESSAGE)
        notification_id = call.data.get(ATTR_NOTIFICATION_ID)

        if notification_id is not None:
            entity_id = ENTITY_ID_FORMAT.format(slugify(notification_id))
        else:
            entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, DEFAULT_OBJECT_ID, opp=opp
            )
            notification_id = entity_id.split(".")[1]

        attr = {}
        if title is not None:
            try:
                title.opp = opp
                title = title.async_render()
            except TemplateError as ex:
                _LOGGER.error("Error rendering title %s: %s", title, ex)
                title = title.template

            attr[ATTR_TITLE] = title

        try:
            message.opp = opp
            message = message.async_render()
        except TemplateError as ex:
            _LOGGER.error("Error rendering message %s: %s", message, ex)
            message = message.template

        attr[ATTR_MESSAGE] = message

        opp.states.async_set(entity_id, STATE, attr)

        # Store notification and fire event
        # This will eventually replace state machine storage
        persistent_notifications[entity_id] = {
            ATTR_MESSAGE: message,
            ATTR_NOTIFICATION_ID: notification_id,
            ATTR_STATUS: STATUS_UNREAD,
            ATTR_TITLE: title,
            ATTR_CREATED_AT: dt_util.utcnow(),
        }

        opp.bus.async_fire(EVENT_PERSISTENT_NOTIFICATIONS_UPDATED)

    @callback
    def dismiss_service(call):
        """Handle the dismiss notification service call."""
        notification_id = call.data.get(ATTR_NOTIFICATION_ID)
        entity_id = ENTITY_ID_FORMAT.format(slugify(notification_id))

        if entity_id not in persistent_notifications:
            return

        opp.states.async_remove(entity_id)

        del persistent_notifications[entity_id]
        opp.bus.async_fire(EVENT_PERSISTENT_NOTIFICATIONS_UPDATED)

    @callback
    def mark_read_service(call):
        """Handle the mark_read notification service call."""
        notification_id = call.data.get(ATTR_NOTIFICATION_ID)
        entity_id = ENTITY_ID_FORMAT.format(slugify(notification_id))

        if entity_id not in persistent_notifications:
            _LOGGER.error(
                "Marking persistent_notification read failed: "
                "Notification ID %s not found.",
                notification_id,
            )
            return

        persistent_notifications[entity_id][ATTR_STATUS] = STATUS_READ
        opp.bus.async_fire(EVENT_PERSISTENT_NOTIFICATIONS_UPDATED)

    opp.services.async_register(
        DOMAIN, SERVICE_CREATE, create_service, SCHEMA_SERVICE_CREATE
    )

    opp.services.async_register(
        DOMAIN, SERVICE_DISMISS, dismiss_service, SCHEMA_SERVICE_DISMISS
    )

    opp.services.async_register(
        DOMAIN, SERVICE_MARK_READ, mark_read_service, SCHEMA_SERVICE_MARK_READ
    )

    opp.components.websocket_api.async_register_command(websocket_get_notifications)

    return True


@callback
@websocket_api.websocket_command({vol.Required("type"): "persistent_notification/get"})
def websocket_get_notifications(
    opp: OpenPeerPower,
    connection: websocket_api.ActiveConnection,
    msg: Mapping[str, Any],
) -> None:
    """Return a list of persistent_notifications."""
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            [
                {
                    key: data[key]
                    for key in (
                        ATTR_NOTIFICATION_ID,
                        ATTR_MESSAGE,
                        ATTR_STATUS,
                        ATTR_TITLE,
                        ATTR_CREATED_AT,
                    )
                }
                for data in opp.data[DOMAIN]["notifications"].values()
            ],
        )
    )
