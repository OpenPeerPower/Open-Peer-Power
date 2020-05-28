"""Set up the demo environment that mimics interaction with devices."""
import asyncio
import logging
import time

from openpeerpower import bootstrap, config_entries
from openpeerpower.const import ATTR_ENTITY_ID, EVENT_OPENPEERPOWER_START
import openpeerpower.core as op

DOMAIN = "demo"
_LOGGER = logging.getLogger(__name__)

COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM = [
    "air_quality",
    "alarm_control_panel",
    "binary_sensor",
    "camera",
    "climate",
    "cover",
    "fan",
    "light",
    "lock",
    "media_player",
    "sensor",
    "switch",
    "vacuum",
    "water_heater",
]

COMPONENTS_WITH_DEMO_PLATFORM = [
    "tts",
    "stt",
    "mailbox",
    "notify",
    "image_processing",
    "calendar",
    "device_tracker",
]


async def async_setup(opp, config):
    """Set up the demo environment."""
    if DOMAIN not in config:
        return True

    if not opp.config_entries.async_entries(DOMAIN):
        opp.async_create_task(
            opp.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
            )
        )

    # Set up demo platforms
    for component in COMPONENTS_WITH_DEMO_PLATFORM:
        opp.async_create_task(
            opp.helpers.discovery.async_load_platform(component, DOMAIN, {}, config)
        )

    config.setdefault(op.DOMAIN, {})
    config.setdefault(DOMAIN, {})

    # Set up sun
    if not opp.config.latitude:
        opp.config.latitude = 32.87336

    if not opp.config.longitude:
        opp.config.longitude = 117.22743

    tasks = [bootstrap.async_setup_component(opp, "sun", config)]

    # Set up input select
    tasks.append(
        bootstrap.async_setup_component(
            opp,
            "input_select",
            {
                "input_select": {
                    "living_room_preset": {
                        "options": ["Visitors", "Visitors with kids", "Home Alone"]
                    },
                    "who_cooks": {
                        "icon": "mdi:panda",
                        "initial": "Anne Therese",
                        "name": "Cook today",
                        "options": ["Paulus", "Anne Therese"],
                    },
                }
            },
        )
    )

    # Set up input boolean
    tasks.append(
        bootstrap.async_setup_component(
            opp,
            "input_boolean",
            {
                "input_boolean": {
                    "notify": {
                        "icon": "mdi:car",
                        "initial": False,
                        "name": "Notify Anne Therese is home",
                    }
                }
            },
        )
    )

    # Set up input boolean
    tasks.append(
        bootstrap.async_setup_component(
            opp,
            "input_number",
            {
                "input_number": {
                    "noise_allowance": {
                        "icon": "mdi:bell-ring",
                        "min": 0,
                        "max": 10,
                        "name": "Allowed Noise",
                        "unit_of_measurement": "dB",
                    }
                }
            },
        )
    )

    results = await asyncio.gather(*tasks)

    if any(not result for result in results):
        return False

    # Set up example persistent notification
    opp.components.persistent_notification.async_create(
        "This is an example of a persistent notification.", title="Example Notification"
    )

    # Set up configurator
    configurator_ids = []
    configurator = opp.components.configurator

    def hue_configuration_callback(data):
        """Fake callback, mark config as done."""
        time.sleep(2)

        # First time it is called, pretend it failed.
        if len(configurator_ids) == 1:
            configurator.notify_errors(
                configurator_ids[0], "Failed to register, please try again."
            )

            configurator_ids.append(0)
        else:
            configurator.request_done(configurator_ids[0])

    request_id = configurator.async_request_config(
        "Philips Hue",
        hue_configuration_callback,
        description=(
            "Press the button on the bridge to register Philips "
            "Hue with Open Peer Power."
        ),
        description_image="/static/images/config_philips_hue.jpg",
        fields=[{"id": "username", "name": "Username"}],
        submit_caption="I have pressed the button",
    )
    configurator_ids.append(request_id)

    async def demo_start_listener(_event):
        """Finish set up."""
        await finish_setup(opp, config)

    opp.bus.async_listen(EVENT_OPENPEERPOWER_START, demo_start_listener)

    return True


async def async_setup_entry(opp, config_entry):
    """Set the config entry up."""
    # Set up demo platforms with config entry
    for component in COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM:
        opp.async_create_task(
            opp.config_entries.async_forward_entry_setup(config_entry, component)
        )
    return True


async def finish_setup(opp, config):
    """Finish set up once demo platforms are set up."""
    switches = None
    lights = None

    while not switches and not lights:
        # Not all platforms might be loaded.
        if switches is not None:
            await asyncio.sleep(0)
        switches = sorted(opp.states.async_entity_ids("switch"))
        lights = sorted(opp.states.async_entity_ids("light"))

    # Set up scripts
    await bootstrap.async_setup_component(
        opp,
        "script",
        {
            "script": {
                "demo": {
                    "alias": "Toggle {}".format(lights[0].split(".")[1]),
                    "sequence": [
                        {
                            "service": "light.turn_off",
                            "data": {ATTR_ENTITY_ID: lights[0]},
                        },
                        {"delay": {"seconds": 5}},
                        {
                            "service": "light.turn_on",
                            "data": {ATTR_ENTITY_ID: lights[0]},
                        },
                        {"delay": {"seconds": 5}},
                        {
                            "service": "light.turn_off",
                            "data": {ATTR_ENTITY_ID: lights[0]},
                        },
                    ],
                }
            }
        },
    )

    # Set up scenes
    await bootstrap.async_setup_component(
        opp,
        "scene",
        {
            "scene": [
                {
                    "name": "Romantic lights",
                    "entities": {
                        lights[0]: True,
                        lights[1]: {
                            "state": "on",
                            "xy_color": [0.33, 0.66],
                            "brightness": 200,
                        },
                    },
                },
                {
                    "name": "Switch on and off",
                    "entities": {switches[0]: True, switches[1]: False},
                },
            ]
        },
    )
