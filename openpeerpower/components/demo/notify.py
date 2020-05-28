"""Demo notification service."""
from openpeerpower.components.notify import BaseNotificationService

EVENT_NOTIFY = "notify"


def get_service(opp, config, discovery_info=None):
    """Get the demo notification service."""
    return DemoNotificationService(opp)


class DemoNotificationService(BaseNotificationService):
    """Implement demo notification service."""

    def __init__(self, opp):
        """Initialize the service."""
        self.opp = opp

    @property
    def targets(self):
        """Return a dictionary of registered targets."""
        return {"test target name": "test target id"}

    def send_message(self, message="", **kwargs):
        """Send a message to a user."""
        kwargs["message"] = message
        self.opp.bus.fire(EVENT_NOTIFY, kwargs)
