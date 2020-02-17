"""HTTP views to interact with the device registry."""
import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.components.websocket_api.decorators import (
    async_response,
    require_admin,
)
from openpeerpower.core import callback
from openpeerpower.helpers.device_registry import async_get_registry

WS_TYPE_LIST = "config/device_registry/list"
SCHEMA_WS_LIST = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_LIST}
)

WS_TYPE_UPDATE = "config/device_registry/update"
SCHEMA_WS_UPDATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_UPDATE,
        vol.Required("device_id"): str,
        vol.Optional("area_id"): vol.Any(str, None),
        vol.Optional("name_by_user"): vol.Any(str, None),
    }
)


async def async_setup(opp):
    """Enable the Device Registry views."""
    opp.components.websocket_api.async_register_command(
        WS_TYPE_LIST, websocket_list_devices, SCHEMA_WS_LIST
    )
    opp.components.websocket_api.async_register_command(
        WS_TYPE_UPDATE, websocket_update_device, SCHEMA_WS_UPDATE
    )
    return True


@async_response
async def websocket_list_devices(opp, connection, msg):
    """Handle list devices command."""
    registry = await async_get_registry(opp)
    connection.send_message(
        websocket_api.result_message(
            msg["id"], [_entry_dict(entry) for entry in registry.devices.values()]
        )
    )


@require_admin
@async_response
async def websocket_update_device(opp, connection, msg):
    """Handle update area websocket command."""
    registry = await async_get_registry(opp)

    msg.pop("type")
    msg_id = msg.pop("id")

    entry = registry.async_update_device(**msg)

    connection.send_message(websocket_api.result_message(msg_id, _entry_dict(entry)))


@callback
def _entry_dict(entry):
    """Convert entry to API format."""
    return {
        "config_entries": list(entry.config_entries),
        "connections": list(entry.connections),
        "manufacturer": entry.manufacturer,
        "model": entry.model,
        "name": entry.name,
        "sw_version": entry.sw_version,
        "id": entry.id,
        "via_device_id": entry.via_device_id,
        "area_id": entry.area_id,
        "name_by_user": entry.name_by_user,
    }
