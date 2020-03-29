"""Test reproduce state for Switch."""
from openpeerpower.core import State

from tests.common import async_mock_service


async def test_reproducing_states(opp, caplog):
    """Test reproducing Switch states."""
    opp.states.async_set("switch.entity_off", "off", {})
    opp.states.async_set("switch.entity_on", "on", {})

    turn_on_calls = async_mock_service(opp, "switch", "turn_on")
    turn_off_calls = async_mock_service(opp, "switch", "turn_off")

    # These calls should do nothing as entities already in desired state
    await opp.helpers.state.async_reproduce_state(
        [State("switch.entity_off", "off"), State("switch.entity_on", "on", {})],
        blocking=True,
    )

    assert len(turn_on_calls) == 0
    assert len(turn_off_calls) == 0

    # Test invalid state is handled
    await opp.helpers.state.async_reproduce_state(
        [State("switch.entity_off", "not_supported")], blocking=True
    )

    assert "not_supported" in caplog.text
    assert len(turn_on_calls) == 0
    assert len(turn_off_calls) == 0

    # Make sure correct services are called
    await opp.helpers.state.async_reproduce_state(
        [
            State("switch.entity_on", "off"),
            State("switch.entity_off", "on", {}),
            # Should not raise
            State("switch.non_existing", "on"),
        ],
        blocking=True,
    )

    assert len(turn_on_calls) == 1
    assert turn_on_calls[0].domain == "switch"
    assert turn_on_calls[0].data == {"entity_id": "switch.entity_off"}

    assert len(turn_off_calls) == 1
    assert turn_off_calls[0].domain == "switch"
    assert turn_off_calls[0].data == {"entity_id": "switch.entity_on"}
