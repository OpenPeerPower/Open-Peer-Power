"""Signal handling related helpers."""
import logging
import signal
import sys
from types import FrameType

from openpeerpower.const import RESTART_EXIT_CODE
from openpeerpower.core import OpenPeerPower, callback
from openpeerpower.loader import bind_opp

_LOGGER = logging.getLogger(__name__)


@callback
@bind_opp
def async_register_signal_handling(opp: OpenPeerPower) -> None:
    """Register system signal handler for core."""
    if sys.platform != "win32":

        @callback
        def async_signal_handle(exit_code: int) -> None:
            """Wrap signal handling.

            * queue call to shutdown task
            * re-instate default handler
            """
            opp.loop.remove_signal_handler(signal.SIGTERM)
            opp.loop.remove_signal_handler(signal.SIGINT)
            opp.async_create_task(opp.async_stop(exit_code))

        try:
            opp.loop.add_signal_handler(signal.SIGTERM, async_signal_handle, 0)
        except ValueError:
            _LOGGER.warning("Could not bind to SIGTERM")

        try:
            opp.loop.add_signal_handler(signal.SIGINT, async_signal_handle, 0)
        except ValueError:
            _LOGGER.warning("Could not bind to SIGINT")

        try:
            opp.loop.add_signal_handler(
                signal.SIGHUP, async_signal_handle, RESTART_EXIT_CODE
            )
        except ValueError:
            _LOGGER.warning("Could not bind to SIGHUP")

    else:
        old_sigterm = None
        old_sigint = None

        @callback
        def async_signal_handle(exit_code: int, frame: FrameType) -> None:
            """Wrap signal handling.

            * queue call to shutdown task
            * re-instate default handler
            """
            signal.signal(signal.SIGTERM, old_sigterm)
            signal.signal(signal.SIGINT, old_sigint)
            opp.async_create_task(opp.async_stop(exit_code))

        try:
            old_sigterm = signal.signal(signal.SIGTERM, async_signal_handle)
        except ValueError:
            _LOGGER.warning("Could not bind to SIGTERM")

        try:
            old_sigint = signal.signal(signal.SIGINT, async_signal_handle)
        except ValueError:
            _LOGGER.warning("Could not bind to SIGINT")
