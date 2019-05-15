"""WebSocket API related errors."""
from homeassistant.exceptions import OpenPeerPowerError


class Disconnect(OpenPeerPowerError):
    """Disconnect the current session."""

    pass
