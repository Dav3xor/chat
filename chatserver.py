import pylws
import chatredis
import random
import itertools
import json

from pprint import pprint

class chat_handler(object):
  def __init__(self, keystart='chat'):
    self.redis               = chatredis.RedisServer(keystart=keystart)

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
                      'new user':{'handler': self.new_user,
                                  'fields':  {'mtype':    type_restraints,
                                              'user':    [str, 24, None], 
                                              'pass':    [str, 16, None]}},
                      'channels':{'handler': self.channels,
                                  'fields':  {'mtype':    type_restraints}},
                      'join':{'handler': self.join,
                              'fields':  {'mtype':    type_restraints, 
                                          'channel': channel_restraints}},
                      'msg': {'handler': self.message,
                              'fields':  {'mtype':    type_restraints,
                                          'to':      channel_restraints, 
                                          'msg':     message_restraints} } }

  def drop_fileno(self, fileno):
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

  

  def authenticate(self, ws, msg, fileno):
    username = msg['user']
    password = msg['pass']
   
    user = self.redis.authenticate(username, password)
    if user:
      # log out existing authenticated user, if existing...
      self.drop_fileno(fileno)

      self.connection_to_user[fileno] = username

      if username not in self.user_to_connections:
        self.user_to_connections[username] = set()
      self.user_to_connections[username].add(fileno)

      self.broadcast(ws,"{mtype:'auth', status:'ok'}",[fileno])
      return True
    else:
      return False

  def new_user(self, ws, msg, fileno):
    username = msg['user']
    password = msg['pass']

    # redis.new_user returns false if the
    # user already exists.
    redis.new_user(username, password)
    return self.authenticate(self, ws, msg, fileno)
       
  def channels(self, ws, msg, fileno):
    channels = self.channel_to_users.keys()
    self.broadcast(ws, channels, (fileno,))
    return True

  def join(self, ws, msg, fileno):
    if fileno not in self.connection_to_user:
      return False
    username     = self.connection_to_user[fileno]
    channel      = msg['channel']

    if username not in self.user_to_channels:
      self.user_to_channels[username] = set()
    self.user_to_channels[username].add(msg['channel'])
    
    if channel not in self.channel_to_users:
      self.channel_to_users[channel] = set()
    self.channel_to_users[channel].add(username)
    return True 
    
  def message(self, ws, msg, fileno):
    if fileno not in self.connection_to_user:
      return False
    username       = self.connection_to_user[fileno]

    channel        = msg['to']
    if channel not in self.channel_to_users:
      return False

    users          = self.channel_to_users[channel]
    if username not in users:
      return False

    msg['from']    = username
    filenos        = list(set(itertools.chain(*[self.user_to_connections[i] for i in users])))

    self.broadcast(ws, msg, filenos)
    return True

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



if __name__ == "__main__":
  handler = chat_handler()
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

