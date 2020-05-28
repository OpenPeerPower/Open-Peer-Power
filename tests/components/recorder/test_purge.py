"""Test data purging."""
from datetime import datetime, timedelta
import json
import unittest
from unittest.mock import patch

from openpeerpower.components import recorder
from openpeerpower.components.recorder.const import DATA_INSTANCE
from openpeerpower.components.recorder.models import Events, States
from openpeerpower.components.recorder.purge import purge_old_data
from openpeerpower.components.recorder.util import session_scope

from tests.common import get_test_open_peer_power, init_recorder_component


class TestRecorderPurge(unittest.TestCase):
    """Base class for common recorder tests."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()
        init_recorder_component(self.opp)
        self.opp.start()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.opp.stop()

    def _add_test_states(self):
        """Add multiple states to the db for testing."""
        now = datetime.now()
        five_days_ago = now - timedelta(days=5)
        eleven_days_ago = now - timedelta(days=11)
        attributes = {"test_attr": 5, "test_attr_10": "nice"}

        self.opp.block_till_done()
        self.opp.data[DATA_INSTANCE].block_till_done()

        with recorder.session_scope(opp=self.opp) as session:
            for event_id in range(6):
                if event_id < 2:
                    timestamp = eleven_days_ago
                    state = "autopurgeme"
                elif event_id < 4:
                    timestamp = five_days_ago
                    state = "purgeme"
                else:
                    timestamp = now
                    state = "dontpurgeme"

                session.add(
                    States(
                        entity_id="test.recorder2",
                        domain="sensor",
                        state=state,
                        attributes=json.dumps(attributes),
                        last_changed=timestamp,
                        last_updated=timestamp,
                        created=timestamp,
                        event_id=event_id + 1000,
                    )
                )

    def _add_test_events(self):
        """Add a few events for testing."""
        now = datetime.now()
        five_days_ago = now - timedelta(days=5)
        eleven_days_ago = now - timedelta(days=11)
        event_data = {"test_attr": 5, "test_attr_10": "nice"}

        self.opp.block_till_done()
        self.opp.data[DATA_INSTANCE].block_till_done()

        with recorder.session_scope(opp=self.opp) as session:
            for event_id in range(6):
                if event_id < 2:
                    timestamp = eleven_days_ago
                    event_type = "EVENT_TEST_AUTOPURGE"
                elif event_id < 4:
                    timestamp = five_days_ago
                    event_type = "EVENT_TEST_PURGE"
                else:
                    timestamp = now
                    event_type = "EVENT_TEST"

                session.add(
                    Events(
                        event_type=event_type,
                        event_data=json.dumps(event_data),
                        origin="LOCAL",
                        created=timestamp,
                        time_fired=timestamp,
                    )
                )

    def test_purge_old_states(self):
        """Test deleting old states."""
        self._add_test_states()
        # make sure we start with 6 states
        with session_scope(opp=self.opp) as session:
            states = session.query(States)
            assert states.count() == 6

            # run purge_old_data()
            purge_old_data(self.opp.data[DATA_INSTANCE], 4, repack=False)

            # we should only have 2 states left after purging
            assert states.count() == 2

    def test_purge_old_events(self):
        """Test deleting old events."""
        self._add_test_events()

        with session_scope(opp=self.opp) as session:
            events = session.query(Events).filter(Events.event_type.like("EVENT_TEST%"))
            assert events.count() == 6

            # run purge_old_data()
            purge_old_data(self.opp.data[DATA_INSTANCE], 4, repack=False)

            # we should only have 2 events left
            assert events.count() == 2

    def test_purge_method(self):
        """Test purge method."""
        service_data = {"keep_days": 4}
        self._add_test_events()
        self._add_test_states()

        # make sure we start with 6 states
        with session_scope(opp=self.opp) as session:
            states = session.query(States)
            assert states.count() == 6

            events = session.query(Events).filter(Events.event_type.like("EVENT_TEST%"))
            assert events.count() == 6

            self.opp.data[DATA_INSTANCE].block_till_done()

            # run purge method - no service data, use defaults
            self.opp.services.call("recorder", "purge")
            self.opp.block_till_done()

            # Small wait for recorder thread
            self.opp.data[DATA_INSTANCE].block_till_done()

            # only purged old events
            assert states.count() == 4
            assert events.count() == 4

            # run purge method - correct service data
            self.opp.services.call("recorder", "purge", service_data=service_data)
            self.opp.block_till_done()

            # Small wait for recorder thread
            self.opp.data[DATA_INSTANCE].block_till_done()

            # we should only have 2 states left after purging
            assert states.count() == 2

            # now we should only have 2 events left
            assert events.count() == 2

            assert not (
                "EVENT_TEST_PURGE" in (event.event_type for event in events.all())
            )

            # run purge method - correct service data, with repack
            with patch(
                "openpeerpower.components.recorder.purge._LOGGER"
            ) as mock_logger:
                service_data["repack"] = True
                self.opp.services.call("recorder", "purge", service_data=service_data)
                self.opp.block_till_done()
                self.opp.data[DATA_INSTANCE].block_till_done()
                assert (
                    mock_logger.debug.mock_calls[3][1][0]
                    == "Vacuuming SQL DB to free space"
                )
