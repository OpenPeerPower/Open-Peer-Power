"""
The methods for loading Open Peer Power components.

Components can be accessed via opp.components.switch from your code.
If you want to retrieve a platform that is part of a component, you should
call get_component(opp, 'switch.your_platform'). 
"""
import functools as ft
import importlib
import logging
import sys
from types import ModuleType

from openpeerpower.const import PLATFORM_FORMAT

_LOGGER = logging.getLogger(__name__)


DATA_KEY = 'components'
PACKAGE_COMPONENTS = 'openpeerpower.components'


def set_component(opp,  # type: OpenPeerPower
                  comp_name: str, component: ModuleType) -> None:
    """Set a component in the cache.

    Async friendly.
    """
    cache = opp.data.get(DATA_KEY)
    if cache is None:
        cache = opp.data[DATA_KEY] = {}
    cache[comp_name] = component

def get_component(opp,  # type: OpenPeerPower
                  comp_or_platform: str) -> ModuleType:
    """Try to load specified component.

    Looks in config dir first, then built-in components.
    Only returns it if also found to be valid.
    Async friendly.
    """
    try:
        return opp.data[DATA_KEY][comp_or_platform]  # type: ignore
    except KeyError:
        pass

    cache = opp.data.get(DATA_KEY)
    if cache is None:
        cache = opp.data[DATA_KEY] = {}

    # First check custom, then built-in
    potential_paths = ['openpeerpower.components.{}'.format(comp_or_platform)]

    for index, path in enumerate(potential_paths):
        try:
            module = importlib.import_module(path)

            # In Python 3 you can import files from directories that do not
            # contain the file __init__.py. A directory is a valid module if
            # it contains a file with the .py extension. In this case Python
            # will succeed in importing the directory as a module and call it
            # a namespace. We do not care about namespaces.
            # This prevents that when only
            # custom_components/switch/some_platform.py exists,
            # the import custom_components.switch would succeed.
            # __file__ was unset for namespaces before Python 3.7
            if getattr(module, '__file__', None) is None:
                continue

            _LOGGER.info("Loaded %s from %s", comp_or_platform, path)

            cache[comp_or_platform] = module

            return module

        except ImportError as err:
            # This error happens if for example custom_components/switch
            # exists and we try to load switch.demo.
            # Ignore errors for custom_components, custom_components.switch
            # and custom_components.switch.demo.
            white_listed_errors = []
            parts = []
            for part in path.split('.'):
                parts.append(part)
                white_listed_errors.append(
                    "No module named '{}'".format('.'.join(parts)))

            if str(err) not in white_listed_errors:
                _LOGGER.exception(
                    ("Error loading %s. Make sure all "
                     "dependencies are installed"), path)

    _LOGGER.error("Unable to find component %s", comp_or_platform)

    return None
