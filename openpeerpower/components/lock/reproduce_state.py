"""Reproduce an Lock state."""
import asyncio
import logging
from typing import Iterable, Optional

from openpeerpower.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_LOCKED,
    STATE_UNLOCKED,
)
from openpeerpower.core import Context, State
from openpeerpower.helpers.typing import OpenPeerPowerType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

VALID_STATES = {STATE_LOCKED, STATE_UNLOCKED}


async def _async_reproduce_state(
    opp: OpenPeerPowerType, state: State, context: Optional[Context] = None
) -> None:
    """Reproduce a single state."""
    cur_state = opp.states.get(state.entity_id)

    if cur_state is None:
        _LOGGER.warning("Unable to find entity %s", state.entity_id)
        return

    if state.state not in VALID_STATES:
        _LOGGER.warning(
            "Invalid state specified for %s: %s", state.entity_id, state.state
        )
        return

    # Return if we are already at the right state.
    if cur_state.state == state.state:
        return

    service_data = {ATTR_ENTITY_ID: state.entity_id}

    if state.state == STATE_LOCKED:
        service = SERVICE_LOCK
    elif state.state == STATE_UNLOCKED:
        service = SERVICE_UNLOCK

    await opp.services.async_call(
        DOMAIN, service, service_data, context=context, blocking=True
    )


async def async_reproduce_states(
    opp: OpenPeerPowerType, states: Iterable[State], context: Optional[Context] = None
) -> None:
    """Reproduce Lock states."""
    await asyncio.gather(
        *(_async_reproduce_state(opp, state, context) for state in states)
    )
