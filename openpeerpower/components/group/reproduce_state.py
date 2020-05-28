"""Module that groups code required to handle state restore for component."""
from typing import Iterable, Optional

from openpeerpower.core import Context, State
from openpeerpower.helpers.state import async_reproduce_state
from openpeerpower.helpers.typing import OpenPeerPowerType

from . import get_entity_ids


async def async_reproduce_states(
    opp: OpenPeerPowerType, states: Iterable[State], context: Optional[Context] = None
) -> None:
    """Reproduce component states."""

    states_copy = []
    for state in states:
        members = get_entity_ids(opp, state.entity_id)
        for member in members:
            states_copy.append(
                State(
                    member,
                    state.state,
                    state.attributes,
                    last_changed=state.last_changed,
                    last_updated=state.last_updated,
                    context=state.context,
                )
            )
    await async_reproduce_state(opp, states_copy, blocking=True, context=context)
