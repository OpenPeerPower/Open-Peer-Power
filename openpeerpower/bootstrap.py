"""Provide methods to bootstrap an Open Peer Power instance."""
import logging
import logging.handlers
import os
import sys
from time import time
from collections import OrderedDict

from openpeerpower import core
from openpeerpower.const import EVENT_OPENPEERPOWER_CLOSE

_LOGGER = logging.getLogger(__name__)

ERROR_LOG_FILENAME = 'open-peer-power.log'

# opp.data key for logging information.
DATA_LOGGING = 'logging'

FIRST_INIT_COMPONENT = {'system_log', 'recorder',
                        'logger', 'introduction', 'history'}

def from_config_dict(config: Any,
                     enable_log: bool = True,
                     verbose: bool = False,
                     log_rotate_days: Any = None,
                     log_file: Any = None,
                     log_no_color: bool = False) \
                     -> Optional[core.OpenPeerPower]:
    """Try to configure Open Peer Power from a configuration dictionary.
    Dynamically loads required components and its dependencies.
    """
    if opp is None:
        opp = core.OpenPeerPower()
    return opp

async def async_from_config_dict(config: Dict[str, Any],
                                 opp: core.HomeAssistant,
                                 config_dir: Optional[str] = None,
                                 enable_log: bool = True,
                                 verbose: bool = False,
                                 skip_pip: bool = False,
                                 log_rotate_days: Any = None,
                                 log_file: Any = None,
                                 log_no_color: bool = False) \
                           -> Optional[core.HomeAssistant]:
    """Try to configure Open Peer Power from a configuration dictionary.

    Dynamically loads required components and its dependencies.
    This method is a coroutine.
    """
    start = time()

    if enable_log:
        async_enable_logging(opp, verbose, log_rotate_days, log_file,
                             log_no_color)

    core_config = config.get(core.DOMAIN, {})
    has_api_password = bool((config.get('http') or {}).get('api_password'))
    has_trusted_networks = bool((config.get('http') or {})
                                .get('trusted_networks'))

    try:
        await conf_util.async_process_ha_core_config(
            opp, core_config, has_api_password, has_trusted_networks)
    except vol.Invalid as config_err:
        conf_util.async_log_exception(
            config_err, 'homeassistant', core_config, opp)
        return None
    except HomeAssistantError:
        _LOGGER.error("Open Peer Power core failed to initialize. "
                      "Further initialization aborted")
        return None

    await opp.async_add_executor_job(
        conf_util.process_ha_config_upgrade, opp)

    opp.config.skip_pip = skip_pip
    if skip_pip:
        _LOGGER.warning("Skipping pip installation of required modules. "
                        "This may cause issues")

    # Make a copy because we are mutating it.
    config = OrderedDict(config)

    # Merge packages
    conf_util.merge_packages_config(
        opp, config, core_config.get(conf_util.CONF_PACKAGES, {}))

    # Ensure we have no None values after merge
    for key, value in config.items():
        if not value:
            config[key] = {}

    opp.config_entries = config_entries.ConfigEntries(opp, config)
    await opp.config_entries.async_load()

    # Filter out the repeating and common config section [homeassistant]
    components = set(key.split(' ')[0] for key in config.keys()
                     if key != core.DOMAIN)
    components.update(opp.config_entries.async_domains())

    await persistent_notification.async_setup(opp, config)

    _LOGGER.info("Open Peer Power core initialized")

    # stage 1
    for component in components:
        if component not in FIRST_INIT_COMPONENT:
            continue
        opp.async_create_task(async_setup_component(opp, component, config))

    await opp.async_block_till_done()

    # stage 2
    for component in components:
        if component in FIRST_INIT_COMPONENT:
            continue
        opp.async_create_task(async_setup_component(opp, component, config))

    await opp.async_block_till_done()

    stop = time()
    _LOGGER.info("Open Peer Power initialized in %.2fs", stop-start)

    return opp


def from_config_file(config_path: str,
                     opp: Optional[core.HomeAssistant] = None,
                     verbose: bool = False,
                     skip_pip: bool = True,
                     log_rotate_days: Any = None,
                     log_file: Any = None,
                     log_no_color: bool = False)\
        -> Optional[core.HomeAssistant]:
    """Read the configuration file and try to start all the functionality.

    Will add functionality to 'opp' parameter if given,
    instantiates a new Open Peer Power object if 'opp' is not given.
    """
    if opp is None:
        opp = core.HomeAssistant()

    return opp

async def async_from_config_file(config_path: str,
                                 opp: core.HomeAssistant,
                                 verbose: bool = False,
                                 skip_pip: bool = True,
                                 log_rotate_days: Any = None,
                                 log_file: Any = None,
                                 log_no_color: bool = False)\
        -> Optional[core.HomeAssistant]:
    """Read the configuration file and try to start all the functionality.
    Will add functionality to 'opp' parameter.
    This method is a coroutine.
    """
    # Set config dir to directory holding config file
    config_dir = os.path.abspath(os.path.dirname(config_path))
    opp.config.config_dir = config_dir

    if not is_virtual_env():
        await async_mount_local_lib_path(config_dir)

    async_enable_logging(opp, verbose, log_rotate_days, log_file,
                         log_no_color)

    try:
        config_dict = await opp.async_add_executor_job(
            conf_util.load_yaml_config_file, config_path)
    except HomeAssistantError as err:
        _LOGGER.error("Error loading %s: %s", config_path, err)
        return None
    finally:
        clear_secret_cache()

    return await async_from_config_dict(
        config_dict, opp, enable_log=False, skip_pip=skip_pip)


@core.callback
def async_enable_logging(opp: core.HomeAssistant,
                         verbose: bool = False,
                         log_rotate_days: Optional[int] = None,
                         log_file: Optional[str] = None,
                         log_no_color: bool = False) -> None:
    """Set up the logging.

    This method must be run in the event loop.
    """
    fmt = ("%(asctime)s %(levelname)s (%(threadName)s) "
           "[%(name)s] %(message)s")
    datefmt = '%Y-%m-%d %H:%M:%S'

    if not log_no_color:
        try:
            from colorlog import ColoredFormatter
            # basicConfig must be called after importing colorlog in order to
            # ensure that the handlers it sets up wraps the correct streams.
            logging.basicConfig(level=logging.INFO)

            colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
            logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
                colorfmt,
                datefmt=datefmt,
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red',
                }
            ))
        except ImportError:
            pass

    # If the above initialization failed for any reason, setup the default
    # formatting.  If the above succeeds, this wil result in a no-op.
    logging.basicConfig(format=fmt, datefmt=datefmt, level=logging.INFO)

    # Suppress overly verbose logs from libraries that aren't helpful
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

    # Log errors to a file if we have write access to file or config dir
    if log_file is None:
        err_log_path = opp.config.path(ERROR_LOG_FILENAME)
    else:
        err_log_path = os.path.abspath(log_file)

    err_path_exists = os.path.isfile(err_log_path)
    err_dir = os.path.dirname(err_log_path)

    # Check if we can write to the error log if it exists or that
    # we can create files in the containing directory if not.
    if (err_path_exists and os.access(err_log_path, os.W_OK)) or \
       (not err_path_exists and os.access(err_dir, os.W_OK)):

        if log_rotate_days:
            err_handler = logging.handlers.TimedRotatingFileHandler(
                err_log_path, when='midnight',
                backupCount=log_rotate_days)  # type: logging.FileHandler
        else:
            err_handler = logging.FileHandler(
                err_log_path, mode='w', delay=True)

        err_handler.setLevel(logging.INFO if verbose else logging.WARNING)
        err_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

        async_handler = AsyncHandler(opp.loop, err_handler)

        async def async_stop_async_handler(_: Any) -> None:
            """Cleanup async handler."""
            logging.getLogger('').removeHandler(async_handler)  # type: ignore
            await async_handler.async_close(blocking=True)

        opp.bus.async_listen_once(
            EVENT_HOMEASSISTANT_CLOSE, async_stop_async_handler)

        logger = logging.getLogger('')
        logger.addHandler(async_handler)  # type: ignore
        logger.setLevel(logging.INFO)

        # Save the log file location for access by other components.
        opp.data[DATA_LOGGING] = err_log_path
    else:
        _LOGGER.error(
            "Unable to set up error log %s (access denied)", err_log_path)


async def async_mount_local_lib_path(config_dir: str) -> str:
    """Add local library to Python Path.

    This function is a coroutine.
    """
    deps_dir = os.path.join(config_dir, 'deps')
    lib_dir = await async_get_user_site(deps_dir)
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    return deps_dir
