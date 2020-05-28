"""Helper to gather system info."""
import os
import platform
from typing import Dict

from openpeerpower.const import __version__ as current_version
from openpeerpower.loader import bind_opp
from openpeerpower.util.package import is_virtual_env

from .typing import OpenPeerPowerType


@bind_opp
async def async_get_system_info(opp: OpenPeerPowerType) -> Dict:
    """Return info about the system."""
    info_object = {
        "version": current_version,
        "dev": "dev" in current_version,
        "oppio": opp.components.oppio.is_oppio(),
        "virtualenv": is_virtual_env(),
        "python_version": platform.python_version(),
        "docker": False,
        "arch": platform.machine(),
        "timezone": str(opp.config.time_zone),
        "os_name": platform.system(),
    }

    if platform.system() == "Windows":
        info_object["os_version"] = platform.win32_ver()[0]
    elif platform.system() == "Darwin":
        info_object["os_version"] = platform.mac_ver()[0]
    elif platform.system() == "FreeBSD":
        info_object["os_version"] = platform.release()
    elif platform.system() == "Linux":
        info_object["docker"] = os.path.isfile("/.dockerenv")

    return info_object
