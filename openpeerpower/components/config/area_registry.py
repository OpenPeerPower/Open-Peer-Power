"""HTTP views to interact with the area registry."""
import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.components.websocket_api.decorators import (
    async_response,
    require_admin,
)
from openpeerpower.core import callback
from openpeerpower.helpers.area_registry import async_get_registry

WS_TYPE_LIST = "config/area_registry/list"
SCHEMA_WS_LIST = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_LIST}
)

WS_TYPE_CREATE = "config/area_registry/create"
SCHEMA_WS_CREATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_CREATE, vol.Required("name"): str}
)

WS_TYPE_DELETE = "config/area_registry/delete"
SCHEMA_WS_DELETE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {vol.Required("type"): WS_TYPE_DELETE, vol.Required("area_id"): str}
)

WS_TYPE_UPDATE = "config/area_registry/update"
SCHEMA_WS_UPDATE = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_UPDATE,
        vol.Required("area_id"): str,
        vol.Required("name"): str,
    }
)


async def async_setup(opp):
    """Enable the Area Registry views."""
    opp.components.websocket_api.async_register_command(
        WS_TYPE_LIST, websocket_list_areas, SCHEMA_WS_LIST
    )
    opp.components.websocket_api.async_register_command(
        WS_TYPE_CREATE, websocket_create_area, SCHEMA_WS_CREATE
    )
    opp.components.websocket_api.async_register_command(
        WS_TYPE_DELETE, websocket_delete_area, SCHEMA_WS_DELETE
    )
    opp.components.websocket_api.async_register_command(
        WS_TYPE_UPDATE, websocket_update_area, SCHEMA_WS_UPDATE
    )
    return True


@async_response
async def websocket_list_areas(opp, connection, msg):
    """Handle list areas command."""
    registry = await async_get_registry(opp)
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            [
                {"name": entry.name, "area_id": entry.id}
                for entry in registry.async_list_areas()
            ],
        )
    )


@require_admin
@async_response
async def websocket_create_area(opp, connection, msg):
    """Create area command."""
    registry = await async_get_registry(opp)
    try:
        entry = registry.async_create(msg["name"])
    except ValueError as err:
        connection.send_message(
            websocket_api.error_message(msg["id"], "invalid_info", str(err))
        )
    else:
        connection.send_message(
            websocket_api.result_message(msg["id"], _entry_dict(entry))
        )


@require_admin
@async_response
async def websocket_delete_area(opp, connection, msg):
    """Delete area command."""
    registry = await async_get_registry(opp)

    try:
        await registry.async_delete(msg["area_id"])
    except KeyError:
        connection.send_message(
            websocket_api.error_message(
                msg["id"], "invalid_info", "Area ID doesn't exist"
            )
        )
    else:
        connection.send_message(websocket_api.result_message(msg["id"], "success"))


@require_admin
@async_response
async def websocket_update_area(opp, connection, msg):
    """Handle update area websocket command."""
    registry = await async_get_registry(opp)

    try:
        entry = registry.async_update(msg["area_id"], msg["name"])
    except ValueError as err:
        connection.send_message(
            websocket_api.error_message(msg["id"], "invalid_info", str(err))
        )
    else:
        connection.send_message(
            websocket_api.result_message(msg["id"], _entry_dict(entry))
        )


@callback
def _entry_dict(entry):
    """Convert entry to API format."""
    return {"area_id": entry.id, "name": entry.name}
