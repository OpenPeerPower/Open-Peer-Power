"""Config flow for DialogFlow."""
from openpeerpower.helpers import config_entry_flow

from .const import DOMAIN

config_entry_flow.register_webhook_flow(
    DOMAIN,
    "Dialogflow Webhook",
    {
        "dialogflow_url": "https://dialogflow.com/docs/fulfillment#webhook",
        "docs_url": "https://www.open-peer-power.io/integrations/dialogflow/",
    },
)
