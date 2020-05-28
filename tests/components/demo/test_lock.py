"""The tests for the Demo lock platform."""
import unittest

from openpeerpower.components import lock
from openpeerpower.setup import setup_component

from tests.common import get_test_open_peer_power, mock_service
from tests.components.lock import common

FRONT = "lock.front_door"
KITCHEN = "lock.kitchen_door"
OPENABLE_LOCK = "lock.openable_lock"


class TestLockDemo(unittest.TestCase):
    """Test the demo lock."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()
        assert setup_component(self.opp, lock.DOMAIN, {"lock": {"platform": "demo"}})

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.opp.stop()

    def test_is_locked(self):
        """Test if lock is locked."""
        assert lock.is_locked(self.opp, FRONT)
        self.opp.states.is_state(FRONT, "locked")

        assert not lock.is_locked(self.opp, KITCHEN)
        self.opp.states.is_state(KITCHEN, "unlocked")

    def test_locking(self):
        """Test the locking of a lock."""
        common.lock(self.opp, KITCHEN)
        self.opp.block_till_done()

        assert lock.is_locked(self.opp, KITCHEN)

    def test_unlocking(self):
        """Test the unlocking of a lock."""
        common.unlock(self.opp, FRONT)
        self.opp.block_till_done()

        assert not lock.is_locked(self.opp, FRONT)

    def test_opening(self):
        """Test the opening of a lock."""
        calls = mock_service(self.opp, lock.DOMAIN, lock.SERVICE_OPEN)
        common.open_lock(self.opp, OPENABLE_LOCK)
        self.opp.block_till_done()
        assert 1 == len(calls)
