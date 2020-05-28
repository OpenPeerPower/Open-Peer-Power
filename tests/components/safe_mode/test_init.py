"""Tests for safe mode integration."""
from openpeerpower.setup import async_setup_component


async def test_works(opp):
    """Test safe mode works."""
    assert await async_setup_component(opp, "safe_mode", {})
    await opp.async_block_till_done()
    assert len(opp.states.async_entity_ids()) == 1
