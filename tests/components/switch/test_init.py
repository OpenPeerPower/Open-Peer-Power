"""The tests for the Switch component."""
# pylint: disable=protected-access
import unittest

from openpeerpower import core
from openpeerpower.components import switch
from openpeerpower.const import CONF_PLATFORM
from openpeerpower.setup import async_setup_component, setup_component

from tests.common import get_test_open_peer_power, mock_entity_platform
from tests.components.switch import common


class TestSwitch(unittest.TestCase):
    """Test the switch module."""

    # pylint: disable=invalid-name
    def setUp(self):
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()
        platform = getattr(self.opp.components, "test.switch")
        platform.init()
        # Switch 1 is ON, switch 2 is OFF
        self.switch_1, self.switch_2, self.switch_3 = platform.ENTITIES

    # pylint: disable=invalid-name
    def tearDown(self):
        """Stop everything that was started."""
        self.opp.stop()

    def test_methods(self):
        """Test is_on, turn_on, turn_off methods."""
        assert setup_component(
            self.opp, switch.DOMAIN, {switch.DOMAIN: {CONF_PLATFORM: "test"}}
        )
        assert switch.is_on(self.opp, self.switch_1.entity_id)
        assert not switch.is_on(self.opp, self.switch_2.entity_id)
        assert not switch.is_on(self.opp, self.switch_3.entity_id)

        common.turn_off(self.opp, self.switch_1.entity_id)
        common.turn_on(self.opp, self.switch_2.entity_id)

        self.opp.block_till_done()

        assert not switch.is_on(self.opp, self.switch_1.entity_id)
        assert switch.is_on(self.opp, self.switch_2.entity_id)

        # Turn all off
        common.turn_off(self.opp)

        self.opp.block_till_done()

        assert not switch.is_on(self.opp, self.switch_1.entity_id)
        assert not switch.is_on(self.opp, self.switch_2.entity_id)
        assert not switch.is_on(self.opp, self.switch_3.entity_id)

        # Turn all on
        common.turn_on(self.opp)

        self.opp.block_till_done()

        assert switch.is_on(self.opp, self.switch_1.entity_id)
        assert switch.is_on(self.opp, self.switch_2.entity_id)
        assert switch.is_on(self.opp, self.switch_3.entity_id)

    def test_setup_two_platforms(self):
        """Test with bad configuration."""
        # Test if switch component returns 0 switches
        test_platform = getattr(self.opp.components, "test.switch")
        test_platform.init(True)

        mock_entity_platform(self.opp, "switch.test2", test_platform)
        test_platform.init(False)

        assert setup_component(
            self.opp,
            switch.DOMAIN,
            {
                switch.DOMAIN: {CONF_PLATFORM: "test"},
                "{} 2".format(switch.DOMAIN): {CONF_PLATFORM: "test2"},
            },
        )


async def test_switch_context(opp, opp_admin_user):
    """Test that switch context works."""
    assert await async_setup_component(opp, "switch", {"switch": {"platform": "test"}})

    await opp.async_block_till_done()

    state = opp.states.get("switch.ac")
    assert state is not None

    await opp.services.async_call(
        "switch",
        "toggle",
        {"entity_id": state.entity_id},
        True,
        core.Context(user_id=opp_admin_user.id),
    )

    state2 = opp.states.get("switch.ac")
    assert state2 is not None
    assert state.state != state2.state
    assert state2.context.user_id == opp_admin_user.id
