"""Test Met weather entity."""


async def test_tracking_home(opp, mock_weather):
    """Test we track home."""
    await opp.config_entries.flow.async_init("met", context={"source": "onboarding"})
    await opp.async_block_till_done()
    assert len(opp.states.async_entity_ids("weather")) == 1
    assert len(mock_weather.mock_calls) == 3

    # Test we track config
    await opp.config.async_update(latitude=10, longitude=20)
    await opp.async_block_till_done()

    assert len(mock_weather.mock_calls) == 6

    entry = opp.config_entries.async_entries()[0]
    await opp.config_entries.async_remove(entry.entry_id)
    assert len(opp.states.async_entity_ids("weather")) == 0


async def test_not_tracking_home(opp, mock_weather):
    """Test when we not track home."""
    await opp.config_entries.flow.async_init(
        "met",
        context={"source": "user"},
        data={"name": "Somewhere", "latitude": 10, "longitude": 20, "elevation": 0},
    )
    await opp.async_block_till_done()
    assert len(opp.states.async_entity_ids("weather")) == 1
    assert len(mock_weather.mock_calls) == 3

    # Test we do not track config
    await opp.config.async_update(latitude=10, longitude=20)
    await opp.async_block_till_done()

    assert len(mock_weather.mock_calls) == 3

    entry = opp.config_entries.async_entries()[0]
    await opp.config_entries.async_remove(entry.entry_id)
    assert len(opp.states.async_entity_ids("weather")) == 0
