#!/usr/bin/env python3.7

"""Start OPP and use WS server to synchronizes component state across clients """
import argparse
import sys
import asyncio
import json
import logging
import websockets
import subprocess
from openpeerpower.const import (
    __version__,
    EVENT_OPENPEERPOWER_START,
    REQUIRED_PYTHON_VER
)
def validate_python() -> None:
    """Validate that the right Python version is running."""
    if sys.version_info[:3] < REQUIRED_PYTHON_VER:
        print("Open Peer Power requires at least Python {}.{}.{}".format(
            *REQUIRED_PYTHON_VER))
        sys.exit(1)

def get_arguments() -> argparse.Namespace:
    """Get parsed passed in arguments."""
    parser = argparse.ArgumentParser(
        description="Open Peer Power: Take Control of your Power.")
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Start Open Peer Power in debug mode')
    parser.add_argument(
        '--skip-pip',
        action='store_true',
        help='Skips pip install of required packages on startup')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging to file.")
    parser.add_argument(
        '--log-rotate-days',
        type=int,
        default=None,
        help='Enables daily log rotation and keeps up to the specified days')
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Log file to write to.  If not set, CONFIG/open-peer-power.log '
             'is used')
    parser.add_argument(
        '--log-no-color',
        action='store_true',
        help="Disable color logs")
    arguments = parser.parse_args()
    return arguments

def setup_and_run_opp() -> int:
    """Set up OPP and run."""
    from openpeerpower import core
    opp = core.OpenPeerPower()

def state_event():
    return json.dumps({'type': 'state', **STATE})


def product_list():
    print('product_list')
    print(prods)
    return json.dumps(prods)

def users_event():
    return json.dumps({'type': 'users', 'count': len(USERS)})

async def notify_state():
    if USERS:       # asyncio.wait doesn't accept an empty list
        message = state_event()
        print('sending state message')
        await asyncio.wait([user.send(message) for user in USERS])

async def notify_users():
    if USERS:       # asyncio.wait doesn't accept an empty list
        message = users_event()
        print('sending user message')
        await asyncio.wait([user.send(message) for user in USERS])

async def notify_products(prods):
    if USERS:       # asyncio.wait doesn't accept an empty list
        message = json.dumps(prods)
        print('sending product list')
        print(message)
        await asyncio.wait(USERS[0].send(message))

async def register(websocket):
    USERS.add(websocket)
#    await notify_users()

async def unregister(websocket):
    USERS.remove(websocket)
    await notify_users()

async def counter(websocket, path):
    # register(websocket) sends user_event() to websocket

    await register(websocket)
    try:
        await websocket.send(state_event())
        async for message in websocket:
            data = json.loads(message)
            if data['action'] == 'minus':
                STATE['value'] -= 1
                await notify_state()
            elif data['action'] == 'plus':
                print('got a plus')
                STATE['value'] += 1
                await notify_state()
            else:
                logging.error(
                    "unsupported event: {}", data)
    finally:
        await unregister(websocket)

async def products(websocket, path):
    # register(websocket) sends product list to websocket
    #await register(websocket)
    #try:
    print('products send')
    await websocket.send(product_list())
    print(product_list())
    async for message in websocket:
        prods = json.loads(message)
      #      await notify_products(prods)
        print('products receive')
        print(prods)
        await websocket.send(message)
    #finally:
    #    await unregister(websocket)

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')

def main() -> int:
    """Start OPP."""
    validate_python()
    args = get_arguments()

    logging.basicConfig()
    global STATE
    STATE = {'value': 0}
    global USERS
    USERS = set()
    PRODUCT_LIST = [
    {'id': 1, 'title': 'Refrigerator', 'price': 10.99, 'inventory': 2},
    {'id': 2, 'title': 'Dishwasher', 'price': 29.99, 'inventory': 10},
    {'id': 3, 'title': 'Washing Machine', 'price': 8.99, 'inventory': 5},
    {'id': 4, 'title': 'Television', 'price': 24.99, 'inventory': 7},
    {'id': 5, 'title': 'Hot Water System', 'price': 11.99, 'inventory': 3}
    ]
    global prods
    prods = PRODUCT_LIST
    #exit_code = setup_and_run_opp()
    print('starting async loop')
    #pid = subprocess.Popen(["python", "scriptname.py"], creationflags=subprocess.DETACHED_PROCESS).pid
    #pid = subprocess.Popen(["c:/temp/OPP-ui/npm", "start"], cwd='c:/temp/OPP-ui').pid
    # latest pid = subprocess.Popen(["npm", "start"], cwd='C:/Users/Paul/Documents/github/OpenPeerPower/OPP-ui').pid
    #asyncio.get_event_loop().run_until_complete(
    #    websockets.serve(counter, 'localhost', 6789))
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(products, 'localhost', 6789))
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    sys.exit(main())
