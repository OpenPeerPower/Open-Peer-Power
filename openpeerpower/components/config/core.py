"""Component to interact with Oppbian tools."""

from openpeerpower.components.http import OpenPeerPowerView
from openpeerpower.config import async_check_op_config_file


async def async_setup(opp):
    """Set up the Oppbian config."""
    opp.http.register_view(CheckConfigView)
    return True


class CheckConfigView(OpenPeerPowerView):
    """Oppbian packages endpoint."""

    url = '/api/config/core/check_config'
    name = 'api:config:core:check_config'

    async def post(self, request):
        """Validate configuration and return results."""
        errors = await async_check_op_config_file(request.app['opp'])

        state = 'invalid' if errors else 'valid'

        return self.json({
            "result": state,
            "errors": errors,
        })
