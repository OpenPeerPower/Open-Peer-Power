"""The tests for the Cast Media player platform."""
# pylint: disable=protected-access
from typing import Optional
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import attr
import pytest

from openpeerpower.components.cast import media_player as cast
from openpeerpower.components.cast.media_player import ChromecastInfo
from openpeerpower.const import EVENT_OPENPEERPOWER_STOP
from openpeerpower.exceptions import PlatformNotReady
from openpeerpower.helpers.dispatcher import async_dispatcher_connect
from openpeerpower.helpers.typing import OpenPeerPowerType
from openpeerpower.setup import async_setup_component

from tests.common import MockConfigEntry, mock_coro


@pytest.fixture(autouse=True)
def cast_mock():
    """Mock pychromecast."""
    pycast_mock = MagicMock()

    with patch(
        "openpeerpower.components.cast.media_player.pychromecast", pycast_mock
    ), patch(
        "openpeerpower.components.cast.discovery.pychromecast", pycast_mock
    ), patch(
        "openpeerpower.components.cast.helpers.dial", MagicMock()
    ), patch(
        "openpeerpower.components.cast.media_player.MultizoneManager", MagicMock()
    ):
        yield


# pylint: disable=invalid-name
FakeUUID = UUID("57355bce-9364-4aa6-ac1e-eb849dccf9e2")
FakeGroupUUID = UUID("57355bce-9364-4aa6-ac1e-eb849dccf9e3")


def get_fake_chromecast(info: ChromecastInfo):
    """Generate a Fake Chromecast object with the specified arguments."""
    mock = MagicMock(host=info.host, port=info.port, uuid=info.uuid)
    mock.media_controller.status = None
    return mock


def get_fake_chromecast_info(
    host="192.168.178.42", port=8009, uuid: Optional[UUID] = FakeUUID
):
    """Generate a Fake ChromecastInfo with the specified arguments."""
    return ChromecastInfo(
        host=host, port=port, uuid=uuid, friendly_name="Speaker", service="the-service"
    )


async def async_setup_cast(opp, config=None, discovery_info=None):
    """Set up the cast platform."""
    if config is None:
        config = {}
    add_entities = Mock()

    await cast.async_setup_platform(
        opp, config, add_entities, discovery_info=discovery_info
    )
    await opp.async_block_till_done()

    return add_entities


async def async_setup_cast_internal_discovery(opp, config=None, discovery_info=None):
    """Set up the cast platform and the discovery."""
    listener = MagicMock(services={})
    browser = MagicMock(zc={})

    with patch(
        "openpeerpower.components.cast.discovery.pychromecast.start_discovery",
        return_value=(listener, browser),
    ) as start_discovery:
        add_entities = await async_setup_cast(opp, config, discovery_info)
        await opp.async_block_till_done()
        await opp.async_block_till_done()

        assert start_discovery.call_count == 1

        discovery_callback = start_discovery.call_args[0][0]

    def discover_chromecast(service_name: str, info: ChromecastInfo) -> None:
        """Discover a chromecast device."""
        listener.services[service_name] = (
            info.host,
            info.port,
            info.uuid,
            info.model_name,
            info.friendly_name,
        )
        discovery_callback(service_name)

    return discover_chromecast, add_entities


async def async_setup_media_player_cast(opp: OpenPeerPowerType, info: ChromecastInfo):
    """Set up the cast platform with async_setup_component."""
    chromecast = get_fake_chromecast(info)

    cast.CastStatusListener = MagicMock()

    with patch(
        "openpeerpower.components.cast.discovery.pychromecast._get_chromecast_from_host",
        return_value=chromecast,
    ) as get_chromecast:
        await async_setup_component(
            opp,
            "media_player",
            {"media_player": {"platform": "cast", "host": info.host}},
        )
        await opp.async_block_till_done()
        assert get_chromecast.call_count == 1
        assert cast.CastStatusListener.call_count == 1
        entity = cast.CastStatusListener.call_args[0][0]
        return chromecast, entity


async def test_start_discovery_called_once(opp):
    """Test pychromecast.start_discovery called exactly once."""
    with patch(
        "openpeerpower.components.cast.discovery.pychromecast.start_discovery",
        return_value=(None, None),
    ) as start_discovery:
        await async_setup_cast(opp)

        assert start_discovery.call_count == 1

        await async_setup_cast(opp)
        assert start_discovery.call_count == 1


async def test_stop_discovery_called_on_stop(opp):
    """Test pychromecast.stop_discovery called on shutdown."""
    browser = MagicMock(zc={})

    with patch(
        "openpeerpower.components.cast.discovery.pychromecast.start_discovery",
        return_value=(None, browser),
    ) as start_discovery:
        # start_discovery should be called with empty config
        await async_setup_cast(opp, {})

        assert start_discovery.call_count == 1

    with patch(
        "openpeerpower.components.cast.discovery.pychromecast.stop_discovery"
    ) as stop_discovery:
        # stop discovery should be called on shutdown
        opp.bus.async_fire(EVENT_OPENPEERPOWER_STOP)
        await opp.async_block_till_done()

        stop_discovery.assert_called_once_with(browser)

    with patch(
        "openpeerpower.components.cast.discovery.pychromecast.start_discovery",
        return_value=(None, browser),
    ) as start_discovery:
        # start_discovery should be called again on re-startup
        await async_setup_cast(opp)

        assert start_discovery.call_count == 1


async def test_internal_discovery_callback_fill_out(opp):
    """Test internal discovery automatically filling out information."""
    import pychromecast  # imports mock pychromecast

    pychromecast.ChromecastConnectionError = IOError

    discover_cast, _ = await async_setup_cast_internal_discovery(opp)
    info = get_fake_chromecast_info(uuid=None)
    full_info = attr.evolve(
        info, model_name="google home", friendly_name="Speaker", uuid=FakeUUID
    )

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=full_info,
    ):
        signal = MagicMock()

        async_dispatcher_connect(opp, "cast_discovered", signal)
        discover_cast("the-service", info)
        await opp.async_block_till_done()

        # when called with incomplete info, it should use HTTP to get missing
        discover = signal.mock_calls[0][1][0]
        assert discover == full_info


async def test_create_cast_device_without_uuid(opp):
    """Test create a cast device with no UUId should still create an entity."""
    info = get_fake_chromecast_info(uuid=None)
    cast_device = cast._async_create_cast_device(opp, info)
    assert cast_device is not None


async def test_create_cast_device_with_uuid(opp):
    """Test create cast devices with UUID creates entities."""
    added_casts = opp.data[cast.ADDED_CAST_DEVICES_KEY] = set()
    info = get_fake_chromecast_info()

    cast_device = cast._async_create_cast_device(opp, info)
    assert cast_device is not None
    assert info.uuid in added_casts

    # Sending second time should not create new entity
    cast_device = cast._async_create_cast_device(opp, info)
    assert cast_device is None


async def test_normal_chromecast_not_starting_discovery(opp):
    """Test cast platform not starting discovery when not required."""
    # pylint: disable=no-member
    with patch(
        "openpeerpower.components.cast.media_player.setup_internal_discovery"
    ) as setup_discovery:
        # normal (non-group) chromecast shouldn't start discovery.
        add_entities = await async_setup_cast(opp, {"host": "host1"})
        await opp.async_block_till_done()
        assert add_entities.call_count == 1
        assert setup_discovery.call_count == 0

        # Same entity twice
        add_entities = await async_setup_cast(opp, {"host": "host1"})
        await opp.async_block_till_done()
        assert add_entities.call_count == 0
        assert setup_discovery.call_count == 0

        opp.data[cast.ADDED_CAST_DEVICES_KEY] = set()
        add_entities = await async_setup_cast(
            opp, discovery_info={"host": "host1", "port": 8009}
        )
        await opp.async_block_till_done()
        assert add_entities.call_count == 1
        assert setup_discovery.call_count == 0

        # group should start discovery.
        opp.data[cast.ADDED_CAST_DEVICES_KEY] = set()
        add_entities = await async_setup_cast(
            opp, discovery_info={"host": "host1", "port": 42}
        )
        await opp.async_block_till_done()
        assert add_entities.call_count == 0
        assert setup_discovery.call_count == 1


async def test_replay_past_chromecasts(opp):
    """Test cast platform re-playing past chromecasts when adding new one."""
    cast_group1 = get_fake_chromecast_info(host="host1", port=42)
    cast_group2 = get_fake_chromecast_info(
        host="host2", port=42, uuid=UUID("9462202c-e747-4af5-a66b-7dce0e1ebc09")
    )

    discover_cast, add_dev1 = await async_setup_cast_internal_discovery(
        opp, discovery_info={"host": "host1", "port": 42}
    )
    discover_cast("service2", cast_group2)
    await opp.async_block_till_done()
    assert add_dev1.call_count == 0

    discover_cast("service1", cast_group1)
    await opp.async_block_till_done()
    await opp.async_block_till_done()  # having tasks that add jobs
    assert add_dev1.call_count == 1

    add_dev2 = await async_setup_cast(opp, discovery_info={"host": "host2", "port": 42})
    await opp.async_block_till_done()
    assert add_dev2.call_count == 1


async def test_entity_media_states(opp: OpenPeerPowerType):
    """Test various entity media states."""
    info = get_fake_chromecast_info()
    full_info = attr.evolve(
        info, model_name="google home", friendly_name="Speaker", uuid=FakeUUID
    )

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=full_info,
    ):
        chromecast, entity = await async_setup_media_player_cast(opp, info)

    entity._available = True
    entity.schedule_update_op_state()
    await opp.async_block_till_done()

    state = opp.states.get("media_player.speaker")
    assert state is not None
    assert state.name == "Speaker"
    assert state.state == "unknown"
    assert entity.unique_id == full_info.uuid

    media_status = MagicMock(images=None)
    media_status.player_is_playing = True
    entity.new_media_status(media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "playing"

    media_status.player_is_playing = False
    media_status.player_is_paused = True
    entity.new_media_status(media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "paused"

    media_status.player_is_paused = False
    media_status.player_is_idle = True
    entity.new_media_status(media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "idle"

    media_status.player_is_idle = False
    chromecast.is_idle = True
    entity.new_media_status(media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "off"

    chromecast.is_idle = False
    entity.new_media_status(media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "unknown"


async def test_group_media_states(opp: OpenPeerPowerType):
    """Test media states are read from group if entity has no state."""
    info = get_fake_chromecast_info()
    full_info = attr.evolve(
        info, model_name="google home", friendly_name="Speaker", uuid=FakeUUID
    )

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=full_info,
    ):
        chromecast, entity = await async_setup_media_player_cast(opp, info)

    entity._available = True
    entity.schedule_update_op_state()
    await opp.async_block_till_done()

    state = opp.states.get("media_player.speaker")
    assert state is not None
    assert state.name == "Speaker"
    assert state.state == "unknown"
    assert entity.unique_id == full_info.uuid

    group_media_status = MagicMock(images=None)
    player_media_status = MagicMock(images=None)

    # Player has no state, group is playing -> Should report 'playing'
    group_media_status.player_is_playing = True
    entity.multizone_new_media_status(str(FakeGroupUUID), group_media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "playing"

    # Player is paused, group is playing -> Should report 'paused'
    player_media_status.player_is_playing = False
    player_media_status.player_is_paused = True
    entity.new_media_status(player_media_status)
    await opp.async_block_till_done()
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "paused"

    # Player is in unknown state, group is playing -> Should report 'playing'
    player_media_status.player_state = "UNKNOWN"
    entity.new_media_status(player_media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "playing"


async def test_dynamic_group_media_states(opp: OpenPeerPowerType):
    """Test media states are read from group if entity has no state."""
    info = get_fake_chromecast_info()
    full_info = attr.evolve(
        info, model_name="google home", friendly_name="Speaker", uuid=FakeUUID
    )

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=full_info,
    ):
        chromecast, entity = await async_setup_media_player_cast(opp, info)

    entity._available = True
    entity.schedule_update_op_state()
    await opp.async_block_till_done()

    state = opp.states.get("media_player.speaker")
    assert state is not None
    assert state.name == "Speaker"
    assert state.state == "unknown"
    assert entity.unique_id == full_info.uuid

    group_media_status = MagicMock(images=None)
    player_media_status = MagicMock(images=None)

    # Player has no state, dynamic group is playing -> Should report 'playing'
    entity._dynamic_group_cast = MagicMock()
    group_media_status.player_is_playing = True
    entity.new_dynamic_group_media_status(group_media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "playing"

    # Player is paused, dynamic group is playing -> Should report 'paused'
    player_media_status.player_is_playing = False
    player_media_status.player_is_paused = True
    entity.new_media_status(player_media_status)
    await opp.async_block_till_done()
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "paused"

    # Player is in unknown state, dynamic group is playing -> Should report
    # 'playing'
    player_media_status.player_state = "UNKNOWN"
    entity.new_media_status(player_media_status)
    await opp.async_block_till_done()
    state = opp.states.get("media_player.speaker")
    assert state.state == "playing"


async def test_group_media_control(opp: OpenPeerPowerType):
    """Test media states are read from group if entity has no state."""
    info = get_fake_chromecast_info()
    full_info = attr.evolve(
        info, model_name="google home", friendly_name="Speaker", uuid=FakeUUID
    )

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=full_info,
    ):
        chromecast, entity = await async_setup_media_player_cast(opp, info)

    entity._available = True
    entity.async_write_op_state()

    state = opp.states.get("media_player.speaker")
    assert state is not None
    assert state.name == "Speaker"
    assert state.state == "unknown"
    assert entity.unique_id == full_info.uuid

    group_media_status = MagicMock(images=None)
    player_media_status = MagicMock(images=None)

    # Player has no state, group is playing -> Should forward calls to group
    group_media_status.player_is_playing = True
    entity.multizone_new_media_status(str(FakeGroupUUID), group_media_status)
    entity.media_play()
    grp_media = entity.mz_mgr.get_multizone_mediacontroller(str(FakeGroupUUID))
    assert grp_media.play.called
    assert not chromecast.media_controller.play.called

    # Player is paused, group is playing -> Should not forward
    player_media_status.player_is_playing = False
    player_media_status.player_is_paused = True
    entity.new_media_status(player_media_status)
    entity.media_pause()
    grp_media = entity.mz_mgr.get_multizone_mediacontroller(str(FakeGroupUUID))
    assert not grp_media.pause.called
    assert chromecast.media_controller.pause.called

    # Player is in unknown state, group is playing -> Should forward to group
    player_media_status.player_state = "UNKNOWN"
    entity.new_media_status(player_media_status)
    entity.media_stop()
    grp_media = entity.mz_mgr.get_multizone_mediacontroller(str(FakeGroupUUID))
    assert grp_media.stop.called
    assert not chromecast.media_controller.stop.called

    # Verify play_media is not forwarded
    entity.play_media(None, None)
    assert not grp_media.play_media.called
    assert chromecast.media_controller.play_media.called


async def test_dynamic_group_media_control(opp: OpenPeerPowerType):
    """Test media states are read from group if entity has no state."""
    info = get_fake_chromecast_info()
    full_info = attr.evolve(
        info, model_name="google home", friendly_name="Speaker", uuid=FakeUUID
    )

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=full_info,
    ):
        chromecast, entity = await async_setup_media_player_cast(opp, info)

    entity._available = True
    entity.schedule_update_op_state()
    entity._dynamic_group_cast = MagicMock()
    await opp.async_block_till_done()

    state = opp.states.get("media_player.speaker")
    assert state is not None
    assert state.name == "Speaker"
    assert state.state == "unknown"
    assert entity.unique_id == full_info.uuid

    group_media_status = MagicMock(images=None)
    player_media_status = MagicMock(images=None)

    # Player has no state, dynamic group is playing -> Should forward
    group_media_status.player_is_playing = True
    entity.new_dynamic_group_media_status(group_media_status)
    entity.media_previous_track()
    assert entity._dynamic_group_cast.media_controller.queue_prev.called
    assert not chromecast.media_controller.queue_prev.called

    # Player is paused, dynamic group is playing -> Should not forward
    player_media_status.player_is_playing = False
    player_media_status.player_is_paused = True
    entity.new_media_status(player_media_status)
    entity.media_next_track()
    assert not entity._dynamic_group_cast.media_controller.queue_next.called
    assert chromecast.media_controller.queue_next.called

    # Player is in unknown state, dynamic group is playing -> Should forward
    player_media_status.player_state = "UNKNOWN"
    entity.new_media_status(player_media_status)
    entity.media_seek(None)
    assert entity._dynamic_group_cast.media_controller.seek.called
    assert not chromecast.media_controller.seek.called

    # Verify play_media is not forwarded
    entity.play_media(None, None)
    assert not entity._dynamic_group_cast.media_controller.play_media.called
    assert chromecast.media_controller.play_media.called


async def test_disconnect_on_stop(opp: OpenPeerPowerType):
    """Test cast device disconnects socket on stop."""
    info = get_fake_chromecast_info()

    with patch(
        "openpeerpower.components.cast.helpers.dial.get_device_status",
        return_value=info,
    ):
        chromecast, _ = await async_setup_media_player_cast(opp, info)

    opp.bus.async_fire(EVENT_OPENPEERPOWER_STOP)
    await opp.async_block_till_done()
    assert chromecast.disconnect.call_count == 1


async def test_entry_setup_no_config(opp: OpenPeerPowerType):
    """Test setting up entry with no config.."""
    await async_setup_component(opp, "cast", {})

    with patch(
        "openpeerpower.components.cast.media_player._async_setup_platform",
        return_value=mock_coro(),
    ) as mock_setup:
        await cast.async_setup_entry(opp, MockConfigEntry(), None)

    assert len(mock_setup.mock_calls) == 1
    assert mock_setup.mock_calls[0][1][1] == {}


async def test_entry_setup_single_config(opp: OpenPeerPowerType):
    """Test setting up entry and having a single config option."""
    await async_setup_component(
        opp, "cast", {"cast": {"media_player": {"host": "bla"}}}
    )

    with patch(
        "openpeerpower.components.cast.media_player._async_setup_platform",
        return_value=mock_coro(),
    ) as mock_setup:
        await cast.async_setup_entry(opp, MockConfigEntry(), None)

    assert len(mock_setup.mock_calls) == 1
    assert mock_setup.mock_calls[0][1][1] == {"host": "bla"}


async def test_entry_setup_list_config(opp: OpenPeerPowerType):
    """Test setting up entry and having multiple config options."""
    await async_setup_component(
        opp, "cast", {"cast": {"media_player": [{"host": "bla"}, {"host": "blu"}]}}
    )

    with patch(
        "openpeerpower.components.cast.media_player._async_setup_platform",
        return_value=mock_coro(),
    ) as mock_setup:
        await cast.async_setup_entry(opp, MockConfigEntry(), None)

    assert len(mock_setup.mock_calls) == 2
    assert mock_setup.mock_calls[0][1][1] == {"host": "bla"}
    assert mock_setup.mock_calls[1][1][1] == {"host": "blu"}


async def test_entry_setup_platform_not_ready(opp: OpenPeerPowerType):
    """Test failed setting up entry will raise PlatformNotReady."""
    await async_setup_component(
        opp, "cast", {"cast": {"media_player": {"host": "bla"}}}
    )

    with patch(
        "openpeerpower.components.cast.media_player._async_setup_platform",
        return_value=mock_coro(exception=Exception),
    ) as mock_setup:
        with pytest.raises(PlatformNotReady):
            await cast.async_setup_entry(opp, MockConfigEntry(), None)

    assert len(mock_setup.mock_calls) == 1
    assert mock_setup.mock_calls[0][1][1] == {"host": "bla"}
