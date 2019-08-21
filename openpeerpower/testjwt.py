#!/usr/bin/python3
#
# Copyright (c) 2017-2018, Fabian Affolter <fabian@affolter-engineering.ch>
# Released under the ASL 2.0 license. See LICENSE.md file for details.
#
import asyncio
import json
import asyncws
import os


#fName = 'C:\\Users\\s69171\\AppData\\Roaming\\.openpeerpower\\access_token.txt'
fName = 'C:\\Users\\Paul\\AppData\\Roaming\\.openpeerpower\\access_token.txt'
AT = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiIwNTY1ZmIyMTJjZDY0OWUzODE3OWE1NjVkNWI2MzI0ZSIsImlhdCI6MTU2NjMwNDI5MSwiZXhwIjoxNTY2MzA2MDkxfQ.scict7xxyhreFxuUYpHN90lf_ttYh3-t40YGZsHvgfQ'


async def main():
    """Simple WebSocket client """
    websocket = await asyncws.connect('ws://localhost:8123/api/websocket')
    while True:
        message = await websocket.recv()
        msg = json.loads(message)
        
        if msg['type'] == 'auth_required':
            if os.path.exists(fName):
                with open(fName, 'r') as f:
                    ACCESS_TOKEN = f.read()
                await websocket.send(json.dumps(
                {'type': 'auth',
                'access_token': ACCESS_TOKEN}
                ))
            else:
                await websocket.send(json.dumps(
                #{ 'type': 'register', 'client_id': 'http://127.0.0.1:8081', 'name': 'Paul', 'username': 'paul','password': 'Boswald0'}
                #))
                { 'type': 'rogin', 'client_id': 'http://127.0.0.1:8081', 'name': 'Paul', 'username': 'paul','api_password': 'Boswald0'}
                ))
        
        if msg['type'] == 'auth_ok':
            if os.path.exists(fName):
                await websocket.send(json.dumps(
                {'id': 2, 'type': 'get_states'}
                ))
            else:
                if msg['access_token']:
                    with open(fName, 'w') as f:
                        f.write(msg['access_token'])
                #await websocket.send(json.dumps(
                #{"id": 1, "type": "auth/long_lived_access_token", "client_name": "paul", "client_icon": '', "lifespan": 365}
            #{'id': 2, 'type': 'subscribe_events', 'event_type': 'state_changed'}
            #))

        if msg['type'] == 'result' and msg['id'] == 1:
            ACCESS_TOKEN = msg['result']
            if os.path.exists(fName):
                pass
            else:
                with open(fName, 'w') as f:
                    f.write(ACCESS_TOKEN)
            await websocket.send(json.dumps(
            {'id': 2, 'type': 'get_states'}
            ))

        if msg['type'] == 'result' and msg['id'] == 2:
            print(message)
            break

        print(message)
        if message is None:
            break

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
