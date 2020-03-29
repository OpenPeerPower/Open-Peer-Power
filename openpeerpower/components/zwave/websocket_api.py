"""Web socket API for Z-Wave."""

import logging

import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.core import callback

from .const import (
    CONF_AUTOHEAL,
    CONF_DEBUG,
    CONF_POLLING_INTERVAL,
    CONF_USB_STICK_PATH,
    DATA_NETWORK,
    DATA_ZWAVE_CONFIG,
)

_LOGGER = logging.getLogger(__name__)

TYPE = "type"
ID = "id"


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required(TYPE): "zwave/network_status"})
def websocket_network_status(opp, connection, msg):
    """Get Z-Wave network status."""
    network = opp.data[DATA_NETWORK]
    connection.send_result(msg[ID], {"state": network.state})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required(TYPE): "zwave/get_config"})
def websocket_get_config(opp, connection, msg):
    """Get Z-Wave configuration."""
    config = opp.data[DATA_ZWAVE_CONFIG]
    connection.send_result(
        msg[ID],
        {
            CONF_AUTOHEAL: config[CONF_AUTOHEAL],
            CONF_DEBUG: config[CONF_DEBUG],
            CONF_POLLING_INTERVAL: config[CONF_POLLING_INTERVAL],
            CONF_USB_STICK_PATH: config[CONF_USB_STICK_PATH],
        },
    )


@callback
def async_load_websocket_api(opp):
    """Set up the web socket API."""
    websocket_api.async_register_command(opp, websocket_network_status)
    websocket_api.async_register_command(opp, websocket_get_config)
