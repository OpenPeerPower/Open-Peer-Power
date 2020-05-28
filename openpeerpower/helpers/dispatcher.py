"""Helpers for Open Peer Power dispatcher & internal component/platform."""
import logging
from typing import Any, Callable

from openpeerpower.core import callback
from openpeerpower.loader import bind_opp
from openpeerpower.util.async_ import run_callback_threadsafe
from openpeerpower.util.logging import catch_log_exception

from .typing import OpenPeerPowerType

_LOGGER = logging.getLogger(__name__)
DATA_DISPATCHER = "dispatcher"


@bind_opp
def dispatcher_connect(
    opp: OpenPeerPowerType, signal: str, target: Callable[..., None]
) -> Callable[[], None]:
    """Connect a callable function to a signal."""
    async_unsub = run_callback_threadsafe(
        opp.loop, async_dispatcher_connect, opp, signal, target
    ).result()

    def remove_dispatcher() -> None:
        """Remove signal listener."""
        run_callback_threadsafe(opp.loop, async_unsub).result()

    return remove_dispatcher


@callback
@bind_opp
def async_dispatcher_connect(
    opp: OpenPeerPowerType, signal: str, target: Callable[..., Any]
) -> Callable[[], None]:
    """Connect a callable function to a signal.

    This method must be run in the event loop.
    """
    if DATA_DISPATCHER not in opp.data:
        opp.data[DATA_DISPATCHER] = {}

    if signal not in opp.data[DATA_DISPATCHER]:
        opp.data[DATA_DISPATCHER][signal] = []

    wrapped_target = catch_log_exception(
        target,
        lambda *args: "Exception in {} when dispatching '{}': {}".format(
            target.__name__, signal, args
        ),
    )

    opp.data[DATA_DISPATCHER][signal].append(wrapped_target)

    @callback
    def async_remove_dispatcher() -> None:
        """Remove signal listener."""
        try:
            opp.data[DATA_DISPATCHER][signal].remove(wrapped_target)
        except (KeyError, ValueError):
            # KeyError is key target listener did not exist
            # ValueError if listener did not exist within signal
            _LOGGER.warning("Unable to remove unknown dispatcher %s", target)

    return async_remove_dispatcher


@bind_opp
def dispatcher_send(opp: OpenPeerPowerType, signal: str, *args: Any) -> None:
    """Send signal and data."""
    opp.loop.call_soon_threadsafe(async_dispatcher_send, opp, signal, *args)


@callback
@bind_opp
def async_dispatcher_send(opp: OpenPeerPowerType, signal: str, *args: Any) -> None:
    """Send signal and data.

    This method must be run in the event loop.
    """
    target_list = opp.data.get(DATA_DISPATCHER, {}).get(signal, [])

    for target in target_list:
        opp.async_add_job(target, *args)
