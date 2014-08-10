import pylws
import random
import itertools
import json

from pprint import pprint

class chat_handler(object):
  def __init__(self):
    self.passwords            = {'Dav3xor':'password', 'User':'x'} 

    # { 1: "Dav3xor", 2: "Frank", 3: "Bob", 4: "Bob" ... }
    self.connection_to_user  = {}

    # { "Dav3xor": [1], "Frank": [2],  "Bob": [3,4] ... }
    self.user_to_connections = {}

    # { "Dav3xor": set(["Dav3stown", "Admin"]), 
    self.user_to_channels    = {}

    # { "Dav3stown": set(["Dav3xor", "Bob", "Frank"]) }
    self.channel_to_users     = {}

    # restraints for fields recieved in json
    # 1. type
    # 2. maxdigits
    # 3. check function (or None)
    type_restraints      = [str, 8, None]
    channel_restraints   = [str, 24, None]
    message_restraints   = [str, 400, None]
    self.msg_types = {'auth':{'handler': self.authenticate,
                              'fields':  {'mtype':    type_restraints,
                                          'user':    [str, 24, None], 
                                          'pass':    [str, 16, None]}},
                      'join':{'handler': self.join,
                              'fields':  {'mtype':    type_restraints, 
                                          'channel': channel_restraints}},
                      'msg': {'handler': self.message,
                              'fields':  {'mtype':    type_restraints,
                                          'to':      channel_restraints, 
                                          'msg':     message_restraints} } }


  def authenticate(self, ws, msg, fileno):
    username = msg['user']
    password = msg['pass']
   

    # TODO: switch over to storing user crap in db
    if (username in self.passwords) and (password == self.passwords[username]): 

      if fileno in self.connection_to_user:
        # we must be changing users (or have a stale fileno) 
        olduser = self.connection_to_user[fileno]
        self.user_to_connections[olduser].remove(fileno)
        if len(self.user_to_connections[olduser]) == 0:
          del(self.user_to_connections[olduser])
          # if there are no more live connections for the current user
          # drop him/her from user_to_channels as well...
          dropchannels = []
          if olduser in self.user_to_channels:
            for channel in self.user_to_channels[olduser]:
              self.channel_to_users[channel].remove(olduser)
              if len(self.channel_to_users[channel]) == 0:
                dropchannels.append(channel)
            for channel in dropchannels:
              del(self.channel_to_users[channel])  
            del(self.user_to_channels[olduser])
      self.connection_to_user[fileno] = username

      if username not in self.user_to_connections:
        self.user_to_connections[username] = set()
      self.user_to_connections[username].add(fileno)

      self.broadcast(ws,"{mtype:'auth', status:'ok'}",[fileno])
      return True
    else:
      return False

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
    filenos        = list(set(itertools.chain(*[self.user_to_connections[i] for i in users])))

    self.broadcast(ws, msg, filenos)


  def broadcast(self, ws, msg, filenos):
    msg = json.dumps(msg)
    return ws.write(filenos, msg)


  def new_connection(self, ws, fd, protocol):
    print "(python) new connection!"
  def closed_connection(self, ws, fd, protocol):
    print "(python) closed connection"
  def recieve_data(self, ws, fd, protocol, msg):
    print "(python) new data -- %s" % msg

    msg = json.loads(msg)
    self.msg_types[msg['mtype']]['handler'](ws, msg, fd)

class WSStub(object):
  def write(self,filenos,msg):
    print str(filenos) + ' - ' + msg

ws = WSStub()
handler = chat_handler()

"""
handler.new_connection(ws,1,"chatzzz")
handler.recieve_data(ws,1,'chat', '{"mtype":"auth","user":"Dav3xor","pass":"password"}')
handler.authenticate(ws, {'mtype': 'auth', 'user':'Dav3xor','pass':'password'},1)
handler.join(ws,{'channel':'Dav3stown'},1)
handler.message(ws,{'to':'Dav3stown','msg':'Hello'},1)
"""


if __name__ == "__main__":
  urls = {'/':                  '/home/dave/dev/chat/index.html',
          '/index.html':        '/home/dave/dev/chat/index.html',
          '/css/offcanvas.css': '/home/dave/dev/chat/css/offcanvas.css',
          '/css/darkstrap.css': '/home/dave/dev/chat/css/darkstrap.css',
          '/css/chat.css':      '/home/dave/dev/chat/css/chat.css',
          '/js/mct.js':         '/home/dave/dev/chat/js/mct.js'}

  listener = pylws.WebSocket('127.0.0.1', 8000,
                             '/home/dave/blah.cert',
                             '/home/dave/blah.key', 
                             {'chat': handler},
                             urls)

  while 1:
    listener.run(100)

