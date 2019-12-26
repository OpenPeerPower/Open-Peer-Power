"""Device automation exceptions."""
from openpeerpower.exceptions import OpenPeerPowerError


class InvalidDeviceAutomationConfig(OpenPeerPowerError):
    """When device automation config is invalid."""
