"""The tests for the demo remote component."""
# pylint: disable=protected-access
import unittest

import openpeerpower.components.remote as remote
from openpeerpower.const import STATE_OFF, STATE_ON
from openpeerpower.setup import setup_component

from tests.common import get_test_open_peer_power
from tests.components.remote import common

ENTITY_ID = "remote.remote_one"


class TestDemoRemote(unittest.TestCase):
    """Test the demo remote."""

    # pylint: disable=invalid-name
    def setUp(self):
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()
        assert setup_component(
            self.opp, remote.DOMAIN, {"remote": {"platform": "demo"}}
        )

    # pylint: disable=invalid-name
    def tearDown(self):
        """Stop down everything that was started."""
        self.opp.stop()

    def test_methods(self):
        """Test if services call the entity methods as expected."""
        common.turn_on(self.opp, entity_id=ENTITY_ID)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_ID)
        assert state.state == STATE_ON

        common.turn_off(self.opp, entity_id=ENTITY_ID)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_ID)
        assert state.state == STATE_OFF

        common.turn_on(self.opp, entity_id=ENTITY_ID)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_ID)
        assert state.state == STATE_ON

        common.send_command(self.opp, "test", entity_id=ENTITY_ID)
        self.opp.block_till_done()
        state = self.opp.states.get(ENTITY_ID)
        assert state.attributes == {
            "friendly_name": "Remote One",
            "last_command_sent": "test",
            "supported_features": 0,
        }
