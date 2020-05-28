"""Support for System health ."""
import asyncio
from collections import OrderedDict
import logging
from typing import Callable, Dict

import async_timeout
import voluptuous as vol

from openpeerpower.components import websocket_api
from openpeerpower.core import callback
from openpeerpower.helpers.typing import ConfigType, OpenPeerPowerType
from openpeerpower.loader import bind_opp

_LOGGER = logging.getLogger(__name__)

DOMAIN = "system_health"

INFO_CALLBACK_TIMEOUT = 5


@bind_opp
@callback
def async_register_info(
    opp: OpenPeerPowerType,
    domain: str,
    info_callback: Callable[[OpenPeerPowerType], Dict],
):
    """Register an info callback."""
    data = opp.data.setdefault(DOMAIN, OrderedDict()).setdefault("info", OrderedDict())
    data[domain] = info_callback


async def async_setup(opp: OpenPeerPowerType, config: ConfigType):
    """Set up the System Health component."""
    opp.components.websocket_api.async_register_command(handle_info)
    return True


async def _info_wrapper(opp, info_callback):
    """Wrap info callback."""
    try:
        with async_timeout.timeout(INFO_CALLBACK_TIMEOUT):
            return await info_callback(opp)
    except asyncio.TimeoutError:
        return {"error": "Fetching info timed out"}
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception("Error fetching info")
        return {"error": str(err)}


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "system_health/info"})
async def handle_info(
    opp: OpenPeerPowerType, connection: websocket_api.ActiveConnection, msg: Dict
):
    """Handle an info request."""
    info_callbacks = opp.data.get(DOMAIN, {}).get("info", {})
    data = OrderedDict()
    data["openpeerpower"] = await opp.helpers.system_info.async_get_system_info()

    if info_callbacks:
        for domain, domain_data in zip(
            info_callbacks,
            await asyncio.gather(
                *(
                    _info_wrapper(opp, info_callback)
                    for info_callback in info_callbacks.values()
                )
            ),
        ):
            data[domain] = domain_data

    connection.send_message(websocket_api.result_message(msg["id"], data))
