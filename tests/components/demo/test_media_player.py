"""The tests for the Demo Media player platform."""
import asyncio
import unittest
from unittest.mock import patch

import pytest
import voluptuous as vol

import openpeerpower.components.media_player as mp
from openpeerpower.helpers.aiohttp_client import DATA_CLIENTSESSION
from openpeerpower.setup import async_setup_component, setup_component

from tests.common import get_test_open_peer_power
from tests.components.media_player import common

entity_id = "media_player.walkman"


class TestDemoMediaPlayer(unittest.TestCase):
    """Test the media_player module."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()

    def tearDown(self):
        """Shut down test instance."""
        self.opp.stop()

    def test_source_select(self):
        """Test the input source service."""
        entity_id = "media_player.lounge_room"

        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        state = self.opp.states.get(entity_id)
        assert "dvd" == state.attributes.get("source")

        with pytest.raises(vol.Invalid):
            common.select_source(self.opp, None, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert "dvd" == state.attributes.get("source")

        common.select_source(self.opp, "xbox", entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert "xbox" == state.attributes.get("source")

    def test_clear_playlist(self):
        """Test clear playlist."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        assert self.opp.states.is_state(entity_id, "playing")

        common.clear_playlist(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "off")

    def test_volume_services(self):
        """Test the volume service."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        state = self.opp.states.get(entity_id)
        assert 1.0 == state.attributes.get("volume_level")

        with pytest.raises(vol.Invalid):
            common.set_volume_level(self.opp, None, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 1.0 == state.attributes.get("volume_level")

        common.set_volume_level(self.opp, 0.5, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 0.5 == state.attributes.get("volume_level")

        common.volume_down(self.opp, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 0.4 == state.attributes.get("volume_level")

        common.volume_up(self.opp, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 0.5 == state.attributes.get("volume_level")

        assert False is state.attributes.get("is_volume_muted")

        with pytest.raises(vol.Invalid):
            common.mute_volume(self.opp, None, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert False is state.attributes.get("is_volume_muted")

        common.mute_volume(self.opp, True, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert True is state.attributes.get("is_volume_muted")

    def test_turning_off_and_on(self):
        """Test turn_on and turn_off."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        assert self.opp.states.is_state(entity_id, "playing")

        common.turn_off(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "off")
        assert not mp.is_on(self.opp, entity_id)

        common.turn_on(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "playing")

        common.toggle(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "off")
        assert not mp.is_on(self.opp, entity_id)

    def test_playing_pausing(self):
        """Test media_pause."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        assert self.opp.states.is_state(entity_id, "playing")

        common.media_pause(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "paused")

        common.media_play_pause(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "playing")

        common.media_play_pause(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "paused")

        common.media_play(self.opp, entity_id)
        self.opp.block_till_done()
        assert self.opp.states.is_state(entity_id, "playing")

    def test_prev_next_track(self):
        """Test media_next_track and media_previous_track ."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        state = self.opp.states.get(entity_id)
        assert 1 == state.attributes.get("media_track")

        common.media_next_track(self.opp, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 2 == state.attributes.get("media_track")

        common.media_next_track(self.opp, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 3 == state.attributes.get("media_track")

        common.media_previous_track(self.opp, entity_id)
        self.opp.block_till_done()
        state = self.opp.states.get(entity_id)
        assert 2 == state.attributes.get("media_track")

        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        ent_id = "media_player.lounge_room"
        state = self.opp.states.get(ent_id)
        assert 1 == state.attributes.get("media_episode")

        common.media_next_track(self.opp, ent_id)
        self.opp.block_till_done()
        state = self.opp.states.get(ent_id)
        assert 2 == state.attributes.get("media_episode")

        common.media_previous_track(self.opp, ent_id)
        self.opp.block_till_done()
        state = self.opp.states.get(ent_id)
        assert 1 == state.attributes.get("media_episode")

    def test_play_media(self):
        """Test play_media ."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        ent_id = "media_player.living_room"
        state = self.opp.states.get(ent_id)
        assert 0 < (mp.SUPPORT_PLAY_MEDIA & state.attributes.get("supported_features"))
        assert state.attributes.get("media_content_id") is not None

        with pytest.raises(vol.Invalid):
            common.play_media(self.opp, None, "some_id", ent_id)
        self.opp.block_till_done()
        state = self.opp.states.get(ent_id)
        assert 0 < (mp.SUPPORT_PLAY_MEDIA & state.attributes.get("supported_features"))
        assert not "some_id" == state.attributes.get("media_content_id")

        common.play_media(self.opp, "youtube", "some_id", ent_id)
        self.opp.block_till_done()
        state = self.opp.states.get(ent_id)
        assert 0 < (mp.SUPPORT_PLAY_MEDIA & state.attributes.get("supported_features"))
        assert "some_id" == state.attributes.get("media_content_id")

    @patch(
        "openpeerpower.components.demo.media_player.DemoYoutubePlayer.media_seek",
        autospec=True,
    )
    def test_seek(self, mock_seek):
        """Test seek."""
        assert setup_component(
            self.opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
        )
        ent_id = "media_player.living_room"
        state = self.opp.states.get(ent_id)
        assert state.attributes["supported_features"] & mp.SUPPORT_SEEK
        assert not mock_seek.called
        with pytest.raises(vol.Invalid):
            common.media_seek(self.opp, None, ent_id)
        self.opp.block_till_done()
        assert not mock_seek.called
        common.media_seek(self.opp, 100, ent_id)
        self.opp.block_till_done()
        assert mock_seek.called


async def test_media_image_proxy(opp, opp_client):
    """Test the media server image proxy server ."""
    assert await async_setup_component(
        opp, mp.DOMAIN, {"media_player": {"platform": "demo"}}
    )

    fake_picture_data = "test.test"

    class MockResponse:
        def __init__(self):
            self.status = 200
            self.headers = {"Content-Type": "sometype"}

        @asyncio.coroutine
        def read(self):
            return fake_picture_data.encode("ascii")

        @asyncio.coroutine
        def release(self):
            pass

    class MockWebsession:
        @asyncio.coroutine
        def get(self, url):
            return MockResponse()

        def detach(self):
            pass

    opp.data[DATA_CLIENTSESSION] = MockWebsession()

    assert opp.states.is_state(entity_id, "playing")
    state = opp.states.get(entity_id)
    client = await opp_client()
    req = await client.get(state.attributes.get("entity_picture"))
    assert req.status == 200
    assert await req.text() == fake_picture_data
