"""WebSocket API related errors."""
from openpeerpower.exceptions import OpenPeerPowerError


class Disconnect(OpenPeerPowerError):
    """Disconnect the current session."""

    pass
