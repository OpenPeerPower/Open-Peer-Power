"""
Starts a service to scan in intervals for new devices.

Will emit EVENT_PLATFORM_DISCOVERED whenever a new service has been discovered.

Knows which components handle certain types, will make sure they are
loaded before the EVENT_PLATFORM_DISCOVERED is fired.
"""
from datetime import timedelta
import json
import logging

from netdisco.discovery import NetworkDiscovery
import voluptuous as vol

from openpeerpower import config_entries
from openpeerpower.const import EVENT_OPENPEERPOWER_START
from openpeerpower.core import callback
import openpeerpower.helpers.config_validation as cv
from openpeerpower.helpers.discovery import async_discover, async_load_platform
from openpeerpower.helpers.event import async_track_point_in_utc_time
import openpeerpower.util.dt as dt_util

DOMAIN = "discovery"

SCAN_INTERVAL = timedelta(seconds=300)
SERVICE_APPLE_TV = "apple_tv"
SERVICE_DAIKIN = "daikin"
SERVICE_DLNA_DMR = "dlna_dmr"
SERVICE_ENIGMA2 = "enigma2"
SERVICE_FREEBOX = "freebox"
SERVICE_OPP_IOS_APP = "opp_ios"
SERVICE_OPPIO = "oppio"
SERVICE_HEOS = "heos"
SERVICE_IGD = "igd"
SERVICE_KONNECTED = "konnected"
SERVICE_MOBILE_APP = "opp_mobile_app"
SERVICE_NETGEAR = "netgear_router"
SERVICE_OCTOPRINT = "octoprint"
SERVICE_PLEX = "plex_mediaserver"
SERVICE_ROKU = "roku"
SERVICE_SABNZBD = "sabnzbd"
SERVICE_SAMSUNG_PRINTER = "samsung_printer"
SERVICE_TELLDUSLIVE = "tellstick"
SERVICE_YEELIGHT = "yeelight"
SERVICE_WEMO = "belkin_wemo"
SERVICE_WINK = "wink"
SERVICE_XIAOMI_GW = "xiaomi_gw"

CONFIG_ENTRY_HANDLERS = {
    SERVICE_DAIKIN: "daikin",
    SERVICE_TELLDUSLIVE: "tellduslive",
    SERVICE_IGD: "upnp",
    SERVICE_PLEX: "plex",
}

SERVICE_HANDLERS = {
    SERVICE_MOBILE_APP: ("mobile_app", None),
    SERVICE_OPP_IOS_APP: ("ios", None),
    SERVICE_NETGEAR: ("device_tracker", None),
    SERVICE_OPPIO: ("oppio", None),
    SERVICE_APPLE_TV: ("apple_tv", None),
    SERVICE_ENIGMA2: ("media_player", "enigma2"),
    SERVICE_ROKU: ("roku", None),
    SERVICE_WINK: ("wink", None),
    SERVICE_XIAOMI_GW: ("xiaomi_aqara", None),
    SERVICE_SABNZBD: ("sabnzbd", None),
    SERVICE_SAMSUNG_PRINTER: ("sensor", "syncthru"),
    SERVICE_KONNECTED: ("konnected", None),
    SERVICE_OCTOPRINT: ("octoprint", None),
    SERVICE_FREEBOX: ("freebox", None),
    SERVICE_YEELIGHT: ("yeelight", None),
    "panasonic_viera": ("media_player", "panasonic_viera"),
    "yamaha": ("media_player", "yamaha"),
    "logitech_mediaserver": ("media_player", "squeezebox"),
    "directv": ("media_player", "directv"),
    "denonavr": ("media_player", "denonavr"),
    "frontier_silicon": ("media_player", "frontier_silicon"),
    "openhome": ("media_player", "openhome"),
    "harmony": ("remote", "harmony"),
    "bose_soundtouch": ("media_player", "soundtouch"),
    "bluesound": ("media_player", "bluesound"),
    "songpal": ("media_player", "songpal"),
    "kodi": ("media_player", "kodi"),
    "volumio": ("media_player", "volumio"),
    "lg_smart_device": ("media_player", "lg_soundbar"),
    "nanoleaf_aurora": ("light", "nanoleaf"),
}

OPTIONAL_SERVICE_HANDLERS = {SERVICE_DLNA_DMR: ("media_player", "dlna_dmr")}

MIGRATED_SERVICE_HANDLERS = [
    "axis",
    "deconz",
    "esphome",
    "google_cast",
    SERVICE_HEOS,
    "homekit",
    "ikea_tradfri",
    "philips_hue",
    "sonos",
    SERVICE_WEMO,
]

DEFAULT_ENABLED = (
    list(CONFIG_ENTRY_HANDLERS) + list(SERVICE_HANDLERS) + MIGRATED_SERVICE_HANDLERS
)
DEFAULT_DISABLED = list(OPTIONAL_SERVICE_HANDLERS) + MIGRATED_SERVICE_HANDLERS

CONF_IGNORE = "ignore"
CONF_ENABLE = "enable"

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Optional(CONF_IGNORE, default=[]): vol.All(
                    cv.ensure_list, [vol.In(DEFAULT_ENABLED)]
                ),
                vol.Optional(CONF_ENABLE, default=[]): vol.All(
                    cv.ensure_list, [vol.In(DEFAULT_DISABLED + DEFAULT_ENABLED)]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(opp, config):
    """Start a discovery service."""

    logger = logging.getLogger(__name__)
    netdisco = NetworkDiscovery()
    already_discovered = set()

    # Disable zeroconf logging, it spams
    logging.getLogger("zeroconf").setLevel(logging.CRITICAL)

    if DOMAIN in config:
        # Platforms ignore by config
        ignored_platforms = config[DOMAIN][CONF_IGNORE]

        # Optional platforms enabled by config
        enabled_platforms = config[DOMAIN][CONF_ENABLE]
    else:
        ignored_platforms = []
        enabled_platforms = []

    for platform in enabled_platforms:
        if platform in DEFAULT_ENABLED:
            logger.warning(
                "Please remove %s from your discovery.enable configuration "
                "as it is now enabled by default",
                platform,
            )

    async def new_service_found(service, info):
        """Handle a new service if one is found."""
        if service in MIGRATED_SERVICE_HANDLERS:
            return

        if service in ignored_platforms:
            logger.info("Ignoring service: %s %s", service, info)
            return

        discovery_hash = json.dumps([service, info], sort_keys=True)
        if discovery_hash in already_discovered:
            logger.debug("Already discovered service %s %s.", service, info)
            return

        already_discovered.add(discovery_hash)

        if service in CONFIG_ENTRY_HANDLERS:
            await opp.config_entries.flow.async_init(
                CONFIG_ENTRY_HANDLERS[service],
                context={"source": config_entries.SOURCE_DISCOVERY},
                data=info,
            )
            return

        comp_plat = SERVICE_HANDLERS.get(service)

        if not comp_plat and service in enabled_platforms:
            comp_plat = OPTIONAL_SERVICE_HANDLERS[service]

        # We do not know how to handle this service.
        if not comp_plat:
            logger.info("Unknown service discovered: %s %s", service, info)
            return

        logger.info("Found new service: %s %s", service, info)

        component, platform = comp_plat

        if platform is None:
            await async_discover(opp, service, info, component, config)
        else:
            await async_load_platform(opp, component, platform, info, config)

    async def scan_devices(now):
        """Scan for devices."""
        try:
            results = await opp.async_add_job(_discover, netdisco)

            for result in results:
                opp.async_create_task(new_service_found(*result))
        except OSError:
            logger.error("Network is unreachable")

        async_track_point_in_utc_time(
            opp, scan_devices, dt_util.utcnow() + SCAN_INTERVAL
        )

    @callback
    def schedule_first(event):
        """Schedule the first discovery when Open Peer Power starts up."""
        async_track_point_in_utc_time(opp, scan_devices, dt_util.utcnow())

    opp.bus.async_listen_once(EVENT_OPENPEERPOWER_START, schedule_first)

    return True


def _discover(netdisco):
    """Discover devices."""
    results = []
    try:
        netdisco.scan()

        for disc in netdisco.discover():
            for service in netdisco.get_info(disc):
                results.append((disc, service))

    finally:
        netdisco.stop()

    return results
