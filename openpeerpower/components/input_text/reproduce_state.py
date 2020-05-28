"""Reproduce an Input text state."""
import asyncio
import logging
from typing import Iterable, Optional

from openpeerpower.const import ATTR_ENTITY_ID
from openpeerpower.core import Context, State
from openpeerpower.helpers.typing import OpenPeerPowerType

from . import ATTR_VALUE, DOMAIN, SERVICE_SET_VALUE

_LOGGER = logging.getLogger(__name__)


async def _async_reproduce_state(
    opp: OpenPeerPowerType, state: State, context: Optional[Context] = None
) -> None:
    """Reproduce a single state."""
    cur_state = opp.states.get(state.entity_id)

    # Return if we can't find the entity
    if cur_state is None:
        _LOGGER.warning("Unable to find entity %s", state.entity_id)
        return

    # Return if we are already at the right state.
    if cur_state.state == state.state:
        return

    # Call service
    service = SERVICE_SET_VALUE
    service_data = {ATTR_ENTITY_ID: state.entity_id, ATTR_VALUE: state.state}

    await opp.services.async_call(
        DOMAIN, service, service_data, context=context, blocking=True
    )


async def async_reproduce_states(
    opp: OpenPeerPowerType, states: Iterable[State], context: Optional[Context] = None
) -> None:
    """Reproduce Input text states."""
    # Reproduce states in parallel.
    await asyncio.gather(
        *(_async_reproduce_state(opp, state, context) for state in states)
    )
