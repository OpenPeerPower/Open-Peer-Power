"""Intents for the cover integration."""
from openpeerpower.core import OpenPeerPower
from openpeerpower.helpers import intent

from . import DOMAIN, SERVICE_CLOSE_COVER, SERVICE_OPEN_COVER

INTENT_OPEN_COVER = "OppOpenCover"
INTENT_CLOSE_COVER = "OppCloseCover"


async def async_setup_intents(opp: OpenPeerPower) -> None:
    """Set up the cover intents."""
    opp.helpers.intent.async_register(
        intent.ServiceIntentHandler(
            INTENT_OPEN_COVER, DOMAIN, SERVICE_OPEN_COVER, "Opened {}"
        )
    )
    opp.helpers.intent.async_register(
        intent.ServiceIntentHandler(
            INTENT_CLOSE_COVER, DOMAIN, SERVICE_CLOSE_COVER, "Closed {}"
        )
    )
