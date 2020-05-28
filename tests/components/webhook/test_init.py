"""Test the webhook component."""
from unittest.mock import Mock

import pytest

from openpeerpower.setup import async_setup_component


@pytest.fixture
def mock_client(opp, opp_client):
    """Create http client for webhooks."""
    opp.loop.run_until_complete(async_setup_component(opp, "webhook", {}))
    return opp.loop.run_until_complete(opp_client())


async def test_unregistering_webhook(opp, mock_client):
    """Test unregistering a webhook."""
    hooks = []
    webhook_id = opp.components.webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    opp.components.webhook.async_register("test", "Test hook", webhook_id, handle)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}")
    assert resp.status == 200
    assert len(hooks) == 1

    opp.components.webhook.async_unregister(webhook_id)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}")
    assert resp.status == 200
    assert len(hooks) == 1


async def test_generate_webhook_url(opp):
    """Test we generate a webhook url correctly."""
    opp.config.api = Mock(base_url="https://example.com")
    url = opp.components.webhook.async_generate_url("some_id")

    assert url == "https://example.com/api/webhook/some_id"


async def test_async_generate_path(opp):
    """Test generating just the path component of the url correctly."""
    path = opp.components.webhook.async_generate_path("some_id")
    assert path == "/api/webhook/some_id"


async def test_posting_webhook_nonexisting(opp, mock_client):
    """Test posting to a nonexisting webhook."""
    resp = await mock_client.post("/api/webhook/non-existing")
    assert resp.status == 200


async def test_posting_webhook_invalid_json(opp, mock_client):
    """Test posting to a nonexisting webhook."""
    opp.components.webhook.async_register("test", "Test hook", "hello", None)
    resp = await mock_client.post("/api/webhook/hello", data="not-json")
    assert resp.status == 200


async def test_posting_webhook_json(opp, mock_client):
    """Test posting a webhook with JSON data."""
    hooks = []
    webhook_id = opp.components.webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append((args[0], args[1], await args[2].text()))

    opp.components.webhook.async_register("test", "Test hook", webhook_id, handle)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}", json={"data": True})
    assert resp.status == 200
    assert len(hooks) == 1
    assert hooks[0][0] is opp
    assert hooks[0][1] == webhook_id
    assert hooks[0][2] == '{"data": true}'


async def test_posting_webhook_no_data(opp, mock_client):
    """Test posting a webhook with no data."""
    hooks = []
    webhook_id = opp.components.webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    opp.components.webhook.async_register("test", "Test hook", webhook_id, handle)

    resp = await mock_client.post(f"/api/webhook/{webhook_id}")
    assert resp.status == 200
    assert len(hooks) == 1
    assert hooks[0][0] is opp
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "POST"
    assert await hooks[0][2].text() == ""


async def test_webhook_put(opp, mock_client):
    """Test sending a put request to a webhook."""
    hooks = []
    webhook_id = opp.components.webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    opp.components.webhook.async_register("test", "Test hook", webhook_id, handle)

    resp = await mock_client.put(f"/api/webhook/{webhook_id}")
    assert resp.status == 200
    assert len(hooks) == 1
    assert hooks[0][0] is opp
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "PUT"


async def test_webhook_head(opp, mock_client):
    """Test sending a head request to a webhook."""
    hooks = []
    webhook_id = opp.components.webhook.async_generate_id()

    async def handle(*args):
        """Handle webhook."""
        hooks.append(args)

    opp.components.webhook.async_register("test", "Test hook", webhook_id, handle)

    resp = await mock_client.head(f"/api/webhook/{webhook_id}")
    assert resp.status == 200
    assert len(hooks) == 1
    assert hooks[0][0] is opp
    assert hooks[0][1] == webhook_id
    assert hooks[0][2].method == "HEAD"


async def test_listing_webhook(opp, opp_ws_client, opp_access_token):
    """Test unregistering a webhook."""
    assert await async_setup_component(opp, "webhook", {})
    client = await opp_ws_client(opp, opp_access_token)

    opp.components.webhook.async_register("test", "Test hook", "my-id", None)

    await client.send_json({"id": 5, "type": "webhook/list"})

    msg = await client.receive_json()
    assert msg["id"] == 5
    assert msg["success"]
    assert msg["result"] == [
        {"webhook_id": "my-id", "domain": "test", "name": "Test hook"}
    ]
