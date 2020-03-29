"""The tests for the Recorder component."""
# pylint: disable=protected-access
import unittest
from unittest.mock import patch

import pytest

from openpeerpower.components.recorder import Recorder
from openpeerpower.components.recorder.const import DATA_INSTANCE
from openpeerpower.components.recorder.models import Events, States
from openpeerpower.components.recorder.util import session_scope
from openpeerpower.const import MATCH_ALL
from openpeerpower.core import callback
from openpeerpower.setup import async_setup_component

from tests.common import get_test_open_peer_power, init_recorder_component


class TestRecorder(unittest.TestCase):
    """Test the recorder module."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()
        init_recorder_component(self.opp)
        self.opp.start()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.opp.stop()

    def test_saving_state(self):
        """Test saving and restoring a state."""
        entity_id = "test.recorder"
        state = "restoring_from_db"
        attributes = {"test_attr": 5, "test_attr_10": "nice"}

        self.opp.states.set(entity_id, state, attributes)

        self.opp.block_till_done()
        self.opp.data[DATA_INSTANCE].block_till_done()

        with session_scope(opp=self.opp) as session:
            db_states = list(session.query(States))
            assert len(db_states) == 1
            assert db_states[0].event_id > 0
            state = db_states[0].to_native()

        assert state == self.opp.states.get(entity_id)

    def test_saving_event(self):
        """Test saving and restoring an event."""
        event_type = "EVENT_TEST"
        event_data = {"test_attr": 5, "test_attr_10": "nice"}

        events = []

        @callback
        def event_listener(event):
            """Record events from eventbus."""
            if event.event_type == event_type:
                events.append(event)

        self.opp.bus.listen(MATCH_ALL, event_listener)

        self.opp.bus.fire(event_type, event_data)

        self.opp.block_till_done()

        assert len(events) == 1
        event = events[0]

        self.opp.data[DATA_INSTANCE].block_till_done()

        with session_scope(opp=self.opp) as session:
            db_events = list(session.query(Events).filter_by(event_type=event_type))
            assert len(db_events) == 1
            db_event = db_events[0].to_native()

        assert event.event_type == db_event.event_type
        assert event.data == db_event.data
        assert event.origin == db_event.origin

        # Recorder uses SQLite and stores datetimes as integer unix timestamps
        assert event.time_fired.replace(microsecond=0) == db_event.time_fired.replace(
            microsecond=0
        )


@pytest.fixture
def opp_recorder():
    """Open Peer Power fixture with in-memory recorder."""
    opp = get_test_open_peer_power()

    def setup_recorder(config=None):
        """Set up with params."""
        init_recorder_component(opp, config)
        opp.start()
        opp.block_till_done()
        opp.data[DATA_INSTANCE].block_till_done()
        return opp

    yield setup_recorder
    opp.stop()


def _add_entities(opp, entity_ids):
    """Add entities."""
    attributes = {"test_attr": 5, "test_attr_10": "nice"}
    for idx, entity_id in enumerate(entity_ids):
        opp.states.set(entity_id, "state{}".format(idx), attributes)
        opp.block_till_done()
    opp.data[DATA_INSTANCE].block_till_done()

    with session_scope(opp=opp) as session:
        return [st.to_native() for st in session.query(States)]


def _add_events(opp, events):
    with session_scope(opp=opp) as session:
        session.query(Events).delete(synchronize_session=False)
    for event_type in events:
        opp.bus.fire(event_type)
        opp.block_till_done()
    opp.data[DATA_INSTANCE].block_till_done()

    with session_scope(opp=opp) as session:
        return [ev.to_native() for ev in session.query(Events)]


# pylint: disable=redefined-outer-name,invalid-name
def test_saving_state_include_domains(opp_recorder):
    """Test saving and restoring a state."""
    opp = opp_recorder({"include": {"domains": "test2"}})
    states = _add_entities(opp, ["test.recorder", "test2.recorder"])
    assert len(states) == 1
    assert opp.states.get("test2.recorder") == states[0]


def test_saving_state_incl_entities(opp_recorder):
    """Test saving and restoring a state."""
    opp = opp_recorder({"include": {"entities": "test2.recorder"}})
    states = _add_entities(opp, ["test.recorder", "test2.recorder"])
    assert len(states) == 1
    assert opp.states.get("test2.recorder") == states[0]


def test_saving_event_exclude_event_type(opp_recorder):
    """Test saving and restoring an event."""
    opp = opp_recorder({"exclude": {"event_types": "test"}})
    events = _add_events(opp, ["test", "test2"])
    assert len(events) == 1
    assert events[0].event_type == "test2"


def test_saving_state_exclude_domains(opp_recorder):
    """Test saving and restoring a state."""
    opp = opp_recorder({"exclude": {"domains": "test"}})
    states = _add_entities(opp, ["test.recorder", "test2.recorder"])
    assert len(states) == 1
    assert opp.states.get("test2.recorder") == states[0]


def test_saving_state_exclude_entities(opp_recorder):
    """Test saving and restoring a state."""
    opp = opp_recorder({"exclude": {"entities": "test.recorder"}})
    states = _add_entities(opp, ["test.recorder", "test2.recorder"])
    assert len(states) == 1
    assert opp.states.get("test2.recorder") == states[0]


def test_saving_state_exclude_domain_include_entity(opp_recorder):
    """Test saving and restoring a state."""
    opp = opp_recorder(
        {"include": {"entities": "test.recorder"}, "exclude": {"domains": "test"}}
    )
    states = _add_entities(opp, ["test.recorder", "test2.recorder"])
    assert len(states) == 2


def test_saving_state_include_domain_exclude_entity(opp_recorder):
    """Test saving and restoring a state."""
    opp = opp_recorder(
        {"exclude": {"entities": "test.recorder"}, "include": {"domains": "test"}}
    )
    states = _add_entities(opp, ["test.recorder", "test2.recorder", "test.ok"])
    assert len(states) == 1
    assert opp.states.get("test.ok") == states[0]
    assert opp.states.get("test.ok").state == "state2"


def test_recorder_setup_failure():
    """Test some exceptions."""
    opp = get_test_open_peer_power()

    with patch.object(Recorder, "_setup_connection") as setup, patch(
        "openpeerpower.components.recorder.time.sleep"
    ):
        setup.side_effect = ImportError("driver not found")
        rec = Recorder(
            opp,
            keep_days=7,
            purge_interval=2,
            uri="sqlite://",
            db_max_retries=10,
            db_retry_wait=3,
            include={},
            exclude={},
        )
        rec.start()
        rec.join()

    opp.stop()


async def test_defaults_set(opp):
    """Test the config defaults are set."""
    recorder_config = None

    async def mock_setup(opp, config):
        """Mock setup."""
        nonlocal recorder_config
        recorder_config = config["recorder"]
        return True

    with patch("openpeerpower.components.recorder.async_setup", side_effect=mock_setup):
        assert await async_setup_component(opp, "history", {})

    assert recorder_config is not None
    assert recorder_config["purge_keep_days"] == 10
    assert recorder_config["purge_interval"] == 1
