"""Reproduce an input boolean state."""
import asyncio
import logging
from typing import Iterable, Optional

from openpeerpower.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from openpeerpower.core import Context, State
from openpeerpower.helpers.typing import OpenPeerPowerType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _async_reproduce_states(
    opp: OpenPeerPowerType, state: State, context: Optional[Context] = None
) -> None:
    """Reproduce input boolean states."""
    cur_state = opp.states.get(state.entity_id)

    if cur_state is None:
        _LOGGER.warning("Unable to find entity %s", state.entity_id)
        return

    if state.state not in (STATE_ON, STATE_OFF):
        _LOGGER.warning(
            "Invalid state specified for %s: %s", state.entity_id, state.state
        )
        return

    if cur_state.state == state.state:
        return

    service = SERVICE_TURN_ON if state.state == STATE_ON else SERVICE_TURN_OFF

    await opp.services.async_call(
        DOMAIN,
        service,
        {ATTR_ENTITY_ID: state.entity_id},
        context=context,
        blocking=True,
    )


async def async_reproduce_states(
    opp: OpenPeerPowerType, states: Iterable[State], context: Optional[Context] = None
) -> None:
    """Reproduce component states."""
    await asyncio.gather(
        *(_async_reproduce_states(opp, state, context) for state in states)
    )
