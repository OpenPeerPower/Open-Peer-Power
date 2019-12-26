"""Network helpers."""
from ipaddress import ip_address
from typing import Optional, cast

import yarl

from openpeerpower.core import OpenPeerPower, callback
from openpeerpower.loader import bind_opp
from openpeerpower.util.network import is_local


@bind_opp
@callback
def async_get_external_url(opp: OpenPeerPower) -> Optional[str]:
    """Get external url of this instance.

    Note: currently it takes 30 seconds after Open Peer Power starts for
    cloud.async_remote_ui_url to work.
    """
    if "cloud" in opp.config.components:
        try:
            return cast(str, opp.components.cloud.async_remote_ui_url())
        except opp.components.cloud.CloudNotAvailable:
            pass

    if opp.config.api is None:
        return None

    base_url = yarl.URL(opp.config.api.base_url)

    try:
        if is_local(ip_address(base_url.host)):
            return None
    except ValueError:
        # ip_address raises ValueError if host is not an IP address
        pass

    return str(base_url)
