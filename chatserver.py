import pylws
import random
import itertools
import json
from pprint import pprint

class chat_handler(object):
  def __init__(self):
    self.users                = {}
    self.channels             = {}
    self.connections          = {}
   
    self.passwords            = {'Dav3xor':'password'} 
    # { 1: "Dav3xor", 2: "Frank", 3: "Bob", 4: "Bob" ... }
    self.connection_to_user  = {}

    # { "Dav3xor": [1], "Frank": [2],  "Bob": [3,4] ... }
    self.user_to_connections = {}

    # { "Dav3xor": set(["Dav3stown", "Admin"]), 
    self.user_to_channels    = {}

    # { "Dav3stown": set(["Dav3xor", "Bob", "Frank"]) }
    self.channel_to_users     = {}

    self.msg_types = {'auth':{'handler': self.authenticate,
                              'fields':  ['type', 'user', 'pass']},
                      'join':{'handler': self.join,
                              'fields':  ['type', 'channel']},
                      'msg': {'handler': self.message,
                              'fields':  ['to', 'msg']} }


  def authenticate(self, ws, msg, fileno):
    username = msg['user']
    password = msg['pass']
    # TODO: switch over to storing user crap in db
    if password == self.passwords[username]:
      print ("User Login --> %s" % (username))
      if username not in self.users:
        self.users[username] = {'connections':[]}
      self.users[username]['connections'].append(fileno)
      self.connection_to_user[fileno] = username
      if username not in self.user_to_connections:
        self.user_to_connections[username] = set()
      self.user_to_connections[username].add(fileno)
    else:
      print ("User Login Failed --> %s" % (username))

  def join(self, ws, msg, fileno):
    username     = self.connection_to_user[fileno]
    channel      = msg['channel']

    if username not in self.user_to_channels:
      self.user_to_channels[username] = set()
    self.user_to_channels[username].add(msg['channel'])
    
    if channel not in self.channel_to_users:
      self.channel_to_users[channel] = set()
    self.channel_to_users[channel].add(username)
    
    print ("Join Channel --> %s to %s " % (username,channel))
    
  def message(self, ws, msg, fileno):
    username       = self.connection_to_user[fileno]
    channel        = msg['to']
    msg['from']    = username
    users          = self.channel_to_users[channel]
    filenos        = itertools.chain(*[self.user_to_connections[i] for i in users])

    self.broadcast(ws, msg, filenos)


  def broadcast(self, ws, msg, filenos):
    msg = json.dumps(msg)
    ws.write(filenos, msg)


  def new_connection(self, ws, fd, protocol):
    print "(python) new connection!"
  def closed_connection(self, ws, fd, protocol):
    print "(python) closed connection"
  def recieve_data(self, ws, fd, protocol, msg):
    print "(python) new data -- %s" % msg

    msg = json.loads(msg)
    self.msg_types[msg['type']]['handler'](ws, msg, fileno)

class WSStub(object):
  def write(self,filenos,msg):
    print msg

ws = WSStub()
handler = chat_handler()
handler.new_connection(ws,1,"chatzzz")
handler.authenticate(ws, {'user':'Dav3xor','pass':'password'},1)
handler.join(ws,{'channel':'Dav3stown'},1)
handler.message(ws,{'to':'Dav3stown','msg':'Hello'},1)

listener = pylws.WebSocket('127.0.0.1', 8000,
                           '/home/dave/blah.cert',
                           '/home/dave/blah.key', 
                           {'chat': handler},
                           {'/':           '/home/dave/dev/chat/index.html',
                            '/index.html': '/home/dave/dev/chat/index.html',
                            '/css/offcanvas.css': '/home/dave/dev/chat/css/offcanvas.css',
                            '/css/darkstrap.css': '/home/dave/dev/chat/css/darkstrap.css',
                            '/js/mct.js': '/home/dave/dev/chat/js/mct.js'})

while 1:
  listener.run(100)

