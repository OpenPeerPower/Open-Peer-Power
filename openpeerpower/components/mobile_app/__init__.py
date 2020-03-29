"""Integrates Native Apps to Open Peer Power."""
import asyncio

from openpeerpower.components import cloud
from openpeerpower.components.webhook import (
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
from openpeerpower.const import CONF_WEBHOOK_ID
from openpeerpower.helpers import device_registry as dr, discovery
from openpeerpower.helpers.typing import ConfigType, OpenPeerPowerType

from .const import (
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_OS_VERSION,
    CONF_CLOUDHOOK_URL,
    DATA_BINARY_SENSOR,
    DATA_CONFIG_ENTRIES,
    DATA_DELETED_IDS,
    DATA_DEVICES,
    DATA_SENSOR,
    DATA_STORE,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .helpers import savable_state
from .http_api import RegistrationsView
from .webhook import handle_webhook

PLATFORMS = "sensor", "binary_sensor", "device_tracker"


async def async_setup(opp: OpenPeerPowerType, config: ConfigType):
    """Set up the mobile app component."""
    store = opp.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    app_config = await store.async_load()
    if app_config is None:
        app_config = {
            DATA_BINARY_SENSOR: {},
            DATA_CONFIG_ENTRIES: {},
            DATA_DELETED_IDS: [],
            DATA_SENSOR: {},
        }

    opp.data[DOMAIN] = {
        DATA_BINARY_SENSOR: app_config.get(DATA_BINARY_SENSOR, {}),
        DATA_CONFIG_ENTRIES: {},
        DATA_DELETED_IDS: app_config.get(DATA_DELETED_IDS, []),
        DATA_DEVICES: {},
        DATA_SENSOR: app_config.get(DATA_SENSOR, {}),
        DATA_STORE: store,
    }

    opp.http.register_view(RegistrationsView())

    for deleted_id in opp.data[DOMAIN][DATA_DELETED_IDS]:
        try:
            webhook_register(
                opp, DOMAIN, "Deleted Webhook", deleted_id, handle_webhook
            )
        except ValueError:
            pass

    opp.async_create_task(
        discovery.async_load_platform(opp, "notify", DOMAIN, {}, config)
    )

    return True


async def async_setup_entry(opp, entry):
    """Set up a mobile_app entry."""
    registration = entry.data

    webhook_id = registration[CONF_WEBHOOK_ID]

    opp.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id] = entry

    device_registry = await dr.async_get_registry(opp)

    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, registration[ATTR_DEVICE_ID])},
        manufacturer=registration[ATTR_MANUFACTURER],
        model=registration[ATTR_MODEL],
        name=registration[ATTR_DEVICE_NAME],
        sw_version=registration[ATTR_OS_VERSION],
    )

    opp.data[DOMAIN][DATA_DEVICES][webhook_id] = device

    registration_name = "Mobile App: {}".format(registration[ATTR_DEVICE_NAME])
    webhook_register(opp, DOMAIN, registration_name, webhook_id, handle_webhook)

    for domain in PLATFORMS:
        opp.async_create_task(
            opp.config_entries.async_forward_entry_setup(entry, domain)
        )

    return True


async def async_unload_entry(opp, entry):
    """Unload a mobile app entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                opp.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    webhook_unregister(opp, entry.data[CONF_WEBHOOK_ID])

    return True


async def async_remove_entry(opp, entry):
    """Cleanup when entry is removed."""
    opp.data[DOMAIN][DATA_DELETED_IDS].append(entry.data[CONF_WEBHOOK_ID])
    store = opp.data[DOMAIN][DATA_STORE]
    await store.async_save(savable_state(opp))

    if CONF_CLOUDHOOK_URL in entry.data:
        try:
            await cloud.async_delete_cloudhook(opp, entry.data[CONF_WEBHOOK_ID])
        except cloud.CloudNotAvailable:
            pass
