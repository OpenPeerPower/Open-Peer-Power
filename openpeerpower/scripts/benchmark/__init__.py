"""Script to run benchmarks."""
import argparse
import asyncio
from contextlib import suppress
from datetime import datetime
import logging
from timeit import default_timer as timer

from openpeerpower import core
from openpeerpower.const import (
    ATTR_NOW, EVENT_STATE_CHANGED, EVENT_TIME_CHANGED)
from openpeerpower.util import dt as dt_util

BENCHMARKS = {}


def run(args):
    """Handle ensure configuration commandline script."""
    # Disable logging
    logging.getLogger('openpeerpower.core').setLevel(logging.CRITICAL)

    parser = argparse.ArgumentParser(
        description=("Run a Open Peer Power benchmark."))
    parser.add_argument('name', choices=BENCHMARKS)
    parser.add_argument('--script', choices=['benchmark'])

    args = parser.parse_args()

    bench = BENCHMARKS[args.name]

    print('Using event loop:', asyncio.get_event_loop_policy().__module__)

    with suppress(KeyboardInterrupt):
        while True:
            loop = asyncio.new_event_loop()
            opp = core.OpenPeerPower(loop)
            opp.async_stop_track_tasks()
            runtime = loop.run_until_complete(bench(opp))
            print('Benchmark {} done in {}s'.format(bench.__name__, runtime))
            loop.run_until_complete(opp.async_stop())
            loop.close()

    return 0


def benchmark(func):
    """Decorate to mark a benchmark."""
    BENCHMARKS[func.__name__] = func
    return func


@benchmark
async def async_million_events(opp):
    """Run a million events."""
    count = 0
    event_name = 'benchmark_event'
    event = asyncio.Event(loop=opp.loop)

    @core.callback
    def listener(_):
        """Handle event."""
        nonlocal count
        count += 1

        if count == 10**6:
            event.set()

    opp.bus.async_listen(event_name, listener)

    for _ in range(10**6):
        opp.bus.async_fire(event_name)

    start = timer()

    await event.wait()

    return timer() - start


@benchmark
async def async_million_time_changed_helper(opp):
    """Run a million events through time changed helper."""
    count = 0
    event = asyncio.Event(loop=opp.loop)

    @core.callback
    def listener(_):
        """Handle event."""
        nonlocal count
        count += 1

        if count == 10**6:
            event.set()

    opp.helpers.event.async_track_time_change(listener, minute=0, second=0)
    event_data = {
        ATTR_NOW: datetime(2017, 10, 10, 15, 0, 0, tzinfo=dt_util.UTC)
    }

    for _ in range(10**6):
        opp.bus.async_fire(EVENT_TIME_CHANGED, event_data)

    start = timer()

    await event.wait()

    return timer() - start


@benchmark
async def async_million_state_changed_helper(opp):
    """Run a million events through state changed helper."""
    count = 0
    entity_id = 'light.kitchen'
    event = asyncio.Event(loop=opp.loop)

    @core.callback
    def listener(*args):
        """Handle event."""
        nonlocal count
        count += 1

        if count == 10**6:
            event.set()

    opp.helpers.event.async_track_state_change(
        entity_id, listener, 'off', 'on')
    event_data = {
        'entity_id': entity_id,
        'old_state': core.State(entity_id, 'off'),
        'new_state': core.State(entity_id, 'on'),
    }

    for _ in range(10**6):
        opp.bus.async_fire(EVENT_STATE_CHANGED, event_data)

    start = timer()

    await event.wait()

    return timer() - start


@benchmark
@asyncio.coroutine
def logbook_filtering_state(opp):
    """Filter state changes."""
    return _logbook_filtering(opp, 1, 1)


@benchmark
@asyncio.coroutine
def logbook_filtering_attributes(opp):
    """Filter attribute changes."""
    return _logbook_filtering(opp, 1, 2)


@benchmark
@asyncio.coroutine
def _logbook_filtering(opp, last_changed, last_updated):
    from openpeerpower.components import logbook

    entity_id = 'test.entity'

    old_state = {
        'entity_id': entity_id,
        'state': 'off'
    }

    new_state = {
        'entity_id': entity_id,
        'state': 'on',
        'last_updated': last_updated,
        'last_changed': last_changed
    }

    event = core.Event(EVENT_STATE_CHANGED, {
        'entity_id': entity_id,
        'old_state': old_state,
        'new_state': new_state
    })

    def yield_events(event):
        # pylint: disable=protected-access
        entities_filter = logbook._generate_filter_from_config({})
        for _ in range(10**5):
            if logbook._keep_event(event, entities_filter):
                yield event

    start = timer()

    list(logbook.humanify(None, yield_events(event)))

    return timer() - start