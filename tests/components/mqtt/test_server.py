"""The tests for the MQTT component embedded server."""
from unittest.mock import MagicMock, Mock

from asynctest import CoroutineMock, patch

import openpeerpower.components.mqtt as mqtt
from openpeerpower.const import CONF_PASSWORD
from openpeerpower.setup import setup_component

from tests.common import get_test_open_peer_power, mock_coro


class TestMQTT:
    """Test the MQTT component."""

    def setup_method(self, method):
        """Set up things to be run when tests are started."""
        self.opp = get_test_open_peer_power()

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.opp.stop()

    @patch("passlib.apps.custom_app_context", Mock(return_value=""))
    @patch("tempfile.NamedTemporaryFile", Mock(return_value=MagicMock()))
    @patch("hbmqtt.broker.Broker", Mock(return_value=MagicMock(start=CoroutineMock())))
    @patch("hbmqtt.broker.Broker.start", Mock(return_value=mock_coro()))
    @patch("openpeerpower.components.mqtt.MQTT")
    def test_creating_config_with_pass_and_no_http_pass(self, mock_mqtt):
        """Test if the MQTT server gets started with password.

        Since 0.77, MQTT server has to set up its own password.
        """
        mock_mqtt().async_connect.return_value = mock_coro(True)
        self.opp.bus.listen_once = MagicMock()
        password = "mqtt_secret"

        assert setup_component(
            self.opp, mqtt.DOMAIN, {mqtt.DOMAIN: {CONF_PASSWORD: password}}
        )
        self.opp.block_till_done()
        assert mock_mqtt.called
        assert mock_mqtt.mock_calls[1][2]["username"] == "openpeerpower"
        assert mock_mqtt.mock_calls[1][2]["password"] == password

    @patch("passlib.apps.custom_app_context", Mock(return_value=""))
    @patch("tempfile.NamedTemporaryFile", Mock(return_value=MagicMock()))
    @patch("hbmqtt.broker.Broker", Mock(return_value=MagicMock(start=CoroutineMock())))
    @patch("hbmqtt.broker.Broker.start", Mock(return_value=mock_coro()))
    @patch("openpeerpower.components.mqtt.MQTT")
    def test_creating_config_with_pass_and_http_pass(self, mock_mqtt):
        """Test if the MQTT server gets started with password.

        Since 0.77, MQTT server has to set up its own password.
        """
        mock_mqtt().async_connect.return_value = mock_coro(True)
        self.opp.bus.listen_once = MagicMock()
        password = "mqtt_secret"

        self.opp.config.api = MagicMock(api_password="api_password")
        assert setup_component(
            self.opp, mqtt.DOMAIN, {mqtt.DOMAIN: {CONF_PASSWORD: password}}
        )
        self.opp.block_till_done()
        assert mock_mqtt.called
        assert mock_mqtt.mock_calls[1][2]["username"] == "openpeerpower"
        assert mock_mqtt.mock_calls[1][2]["password"] == password

    @patch("tempfile.NamedTemporaryFile", Mock(return_value=MagicMock()))
    @patch("hbmqtt.broker.Broker.start", return_value=mock_coro())
    def test_broker_config_fails(self, mock_run):
        """Test if the MQTT component fails if server fails."""
        from hbmqtt.broker import BrokerException

        mock_run.side_effect = BrokerException

        self.opp.config.api = MagicMock(api_password=None)

        assert not setup_component(
            self.opp, mqtt.DOMAIN, {mqtt.DOMAIN: {mqtt.CONF_EMBEDDED: {}}}
        )
