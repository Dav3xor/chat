from websocket import create_connection
import json
import socket

ws = create_connection("ws://127.0.0.1:8000/",
                       sockopt=((socket.IPPROTO_TCP, socket.TCP_NODELAY,1),) )
ws.send(json.dumps({'type': 'auth', 
                    'user': 'dave', 
                    'pass':'password'}))
ws.send(json.dumps({'type': 'join', 
                    'channel': 'ch'}))
#ws.recv()

