"""Test util methods."""
from unittest.mock import MagicMock, patch

import pytest

from openpeerpower.components.recorder import util
from openpeerpower.components.recorder.const import DATA_INSTANCE

from tests.common import get_test_open_peer_power, init_recorder_component


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


def test_recorder_bad_commit(opp_recorder):
    """Bad _commit should retry 3 times."""
    opp = opp_recorder()

    def work(session):
        """Bad work."""
        session.execute("select * from notthere")

    with patch(
        "openpeerpower.components.recorder.time.sleep"
    ) as e_mock, util.session_scope(opp=opp) as session:
        res = util.commit(session, work)
    assert res is False
    assert e_mock.call_count == 3


def test_recorder_bad_execute(opp_recorder):
    """Bad execute, retry 3 times."""
    from sqlalchemy.exc import SQLAlchemyError

    opp_recorder()

    def to_native():
        """Rasie exception."""
        raise SQLAlchemyError()

    mck1 = MagicMock()
    mck1.to_native = to_native

    with pytest.raises(SQLAlchemyError), patch(
        "openpeerpower.components.recorder.time.sleep"
    ) as e_mock:
        util.execute((mck1,))

    assert e_mock.call_count == 2
