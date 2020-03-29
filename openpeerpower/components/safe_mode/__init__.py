"""The Safe Mode integration."""
from openpeerpower.components import persistent_notification
from openpeerpower.core import OpenPeerPower

DOMAIN = "safe_mode"


async def async_setup(opp: OpenPeerPower, config: dict):
    """Set up the Safe Mode component."""
    persistent_notification.async_create(
        opp,
        "Open Peer Power is running in safe mode. Check [the error log](/developer-tools/logs) to see what went wrong.",
        "Safe Mode",
    )
    return True
