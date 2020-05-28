"""Support for Zigbee Home Automation devices."""

import logging

import voluptuous as vol

from openpeerpower import config_entries, const as op_const
import openpeerpower.helpers.config_validation as cv
from openpeerpower.helpers.device_registry import CONNECTION_ZIGBEE

from . import api
from .core import ZHAGateway
from .core.const import (
    COMPONENTS,
    CONF_BAUDRATE,
    CONF_DATABASE,
    CONF_DEVICE_CONFIG,
    CONF_ENABLE_QUIRKS,
    CONF_RADIO_TYPE,
    CONF_USB_PATH,
    DATA_ZHA,
    DATA_ZHA_CONFIG,
    DATA_ZHA_DISPATCHERS,
    DATA_ZHA_GATEWAY,
    DEFAULT_BAUDRATE,
    DEFAULT_RADIO_TYPE,
    DOMAIN,
    RadioType,
)

DEVICE_CONFIG_SCHEMA_ENTRY = vol.Schema({vol.Optional(op_const.CONF_TYPE): cv.string})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_RADIO_TYPE, default=DEFAULT_RADIO_TYPE): cv.enum(
                    RadioType
                ),
                CONF_USB_PATH: cv.string,
                vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): cv.positive_int,
                vol.Optional(CONF_DATABASE): cv.string,
                vol.Optional(CONF_DEVICE_CONFIG, default={}): vol.Schema(
                    {cv.string: DEVICE_CONFIG_SCHEMA_ENTRY}
                ),
                vol.Optional(CONF_ENABLE_QUIRKS, default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Zigbee definitions
CENTICELSIUS = "C-100"

# Internal definitions
_LOGGER = logging.getLogger(__name__)


async def async_setup(opp, config):
    """Set up ZHA from config."""
    opp.data[DATA_ZHA] = {}

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    opp.data[DATA_ZHA][DATA_ZHA_CONFIG] = conf

    if not opp.config_entries.async_entries(DOMAIN):
        opp.async_create_task(
            opp.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={
                    CONF_USB_PATH: conf[CONF_USB_PATH],
                    CONF_RADIO_TYPE: conf.get(CONF_RADIO_TYPE).value,
                },
            )
        )
    return True


async def async_setup_entry(opp, config_entry):
    """Set up ZHA.

    Will automatically load components to support devices found on the network.
    """

    for component in COMPONENTS:
        opp.data[DATA_ZHA][component] = opp.data[DATA_ZHA].get(component, {})

    opp.data[DATA_ZHA] = opp.data.get(DATA_ZHA, {})
    opp.data[DATA_ZHA][DATA_ZHA_DISPATCHERS] = []
    config = opp.data[DATA_ZHA].get(DATA_ZHA_CONFIG, {})

    if config.get(CONF_ENABLE_QUIRKS, True):
        # needs to be done here so that the ZHA module is finished loading
        # before zhaquirks is imported
        import zhaquirks  # noqa: F401 pylint: disable=unused-import, import-outside-toplevel, import-error

    zha_gateway = ZHAGateway(opp, config, config_entry)
    await zha_gateway.async_initialize()

    device_registry = await opp.helpers.device_registry.async_get_registry()
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(CONNECTION_ZIGBEE, str(zha_gateway.application_controller.ieee))},
        identifiers={(DOMAIN, str(zha_gateway.application_controller.ieee))},
        name="Zigbee Coordinator",
        manufacturer="ZHA",
        model=zha_gateway.radio_description,
    )

    for component in COMPONENTS:
        opp.async_create_task(
            opp.config_entries.async_forward_entry_setup(config_entry, component)
        )

    api.async_load_api(opp)

    async def async_zha_shutdown(event):
        """Handle shutdown tasks."""
        await opp.data[DATA_ZHA][DATA_ZHA_GATEWAY].shutdown()
        await opp.data[DATA_ZHA][DATA_ZHA_GATEWAY].async_update_device_storage()

    opp.bus.async_listen_once(op_const.EVENT_OPENPEERPOWER_STOP, async_zha_shutdown)
    return True


async def async_unload_entry(opp, config_entry):
    """Unload ZHA config entry."""
    await opp.data[DATA_ZHA][DATA_ZHA_GATEWAY].shutdown()

    api.async_unload_api(opp)

    dispatchers = opp.data[DATA_ZHA].get(DATA_ZHA_DISPATCHERS, [])
    for unsub_dispatcher in dispatchers:
        unsub_dispatcher()

    for component in COMPONENTS:
        await opp.config_entries.async_forward_entry_unload(config_entry, component)

    return True
