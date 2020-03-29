"""Demo platform for the Device tracker component."""
import random

from .const import DOMAIN, SERVICE_RANDOMIZE_DEVICE_TRACKER_DATA


def setup_scanner(opp, config, see, discovery_info=None):
    """Set up the demo tracker."""

    def offset():
        """Return random offset."""
        return (random.randrange(500, 2000)) / 2e5 * random.choice((-1, 1))

    def random_see(dev_id, name):
        """Randomize a sighting."""
        see(
            dev_id=dev_id,
            host_name=name,
            gps=(opp.config.latitude + offset(), opp.config.longitude + offset()),
            gps_accuracy=random.randrange(50, 150),
            battery=random.randrange(10, 90),
        )

    def observe(call=None):
        """Observe three entities."""
        random_see("demo_paulus", "Paulus")
        random_see("demo_anne_therese", "Anne Therese")

    observe()

    see(
        dev_id="demo_home_boy",
        host_name="Home Boy",
        gps=[opp.config.latitude - 0.00002, opp.config.longitude + 0.00002],
        gps_accuracy=20,
        battery=53,
    )

    opp.services.register(DOMAIN, SERVICE_RANDOMIZE_DEVICE_TRACKER_DATA, observe)

    return True
