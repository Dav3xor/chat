import time
import struct
import socket
import hashlib
import base64
import sys
from select import select
import re
import logging
from threading import Thread
import signal
import json

# Simple WebSocket server implementation. Handshakes with the client then echos back everything
# that is received. Has no dependencies (doesn't require Twisted etc) and works with the RFC6455
# version of WebSockets. Tested with FireFox 16, though should work with the latest versions of
# IE, Chrome etc.
#
# rich20b@gmail.com
# Adapted from https://gist.github.com/512987 with various functions stolen from other sites, see
# below for full details.
 
# Constants
MAGIC_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
TEXT = 0x01
BINARY = 0x02

passwords = {'dave':'password', 'joe':'morepassword'}
namemap = {}

class ChatServer(object):
  def __init__(self, bind, port, cls):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.socket.bind((bind, port))
    self.bind = bind
    self.port = port
    self.cls = cls
    self.listeners = [self.socket]
    
    self.users                = {}
    self.channels             = {}
    self.connections          = {}

    # msg comes in, find user with fileno
    self.msg_types = {'auth':{'handler': self.authenticate,
                              'fields':  ['type', 'user', 'pass']},
                      'join':{'handler': self.join,
                              'fields':  ['type', 'channel']},
                      'msg': {'handler': self.message,
                              'fields':  ['type', 'to', 'text', 'mode']} }
                

    # { 1: "Dav3xor", 2: "Frank", 3: "Bob", 4: "Bob" ... }
    self.connection_to_user  = {}

    # { "Dav3xor": [1], "Frank": [2],  "Bob": [3,4] ... }
    self.user_to_connections = {}

    # { "Dav3xor": set(["Dav3stown", "Admin"]), 
    self.users_to_channels    = {}

    # { "Dav3stown": set(["Dav3xor", "Bob", "Frank"]) }
    self.channel_to_users     = {}

  def dispatch(self, msg, fileno):
    logging.info("Msg --> %s" % msg)
    msg = json.loads(msg)
    self.msg_types[msg['type']]['handler'](msg, fileno)

  def listen(self, backlog=5):

    self.socket.listen(backlog)
    logging.info("Listening on %s" % self.port)

    # Keep serving requests
    self.running = True
    while self.running:
    
      # Find clients that need servicing
      rList, wList, xList = select(self.listeners, [], self.listeners, 1)
      for ready in rList:
        if ready == self.socket:
          logging.debug("New client connection")
          client, address = self.socket.accept()
          fileno = client.fileno()
          self.listeners.append(fileno)
          self.connections[fileno] = self.cls(client, self)
        else:
          logging.debug("Client ready for reading %s" % ready)
          client = self.connections[ready].client
          data = client.recv(4096)
          fileno = client.fileno()
          if data:
            msg = self.connections[fileno].decode(data)
            if msg:
              self.dispatch(msg, fileno)
          else:
            logging.debug("Closing client %s" % ready)
            self.connections[fileno].close()
            del self.connections[fileno]
            self.listeners.remove(ready)
      
    # Step though and delete broken connections
    for failed in xList:
      if failed == self.socket:
        logging.error("Socket broke")
        for connection in self.connections:
          connection.close()
        self.running = False

  def authenticate(self, msg, fileno):
    username = msg['user']
    password = msg['pass']
    # TODO: switch over to storing user crap in db
    if password == passwords[username]:
      logging.info("User Login --> %s" % (username))
      self.addUserConnection(username, fileno)
    else:
      logging.info("User Login Failed --> %s" % (username))

  def join(self, msg, fileno):
    username     = self.connection_to_user(fileno)
    channel      = msg['channel']

    if not self.users_to_channels.has_key[username]:
      self.users_to_channels[username] = set()
    self.users_to_channels[username].add(msg['channel'])
    
    if not self.channel_to_users.has_key[channel]:
      self.channel_to_users[channel] = set()
    self.channel_to_users[channel].add(username)
    
    logging.info("Join Channel --> %s to %s " % (username,channel))
    
  def message(self, msg, fileno):
    username     = self.connection_to_user(fileno)
    if msg['mode'] == 'to channel':
      channel        = msg['to']
      msg['from']    = username
      users          = self.channel_to_users[channel]
      filenos        = itertools.chain(*[self.user_to_connections[i] for i in users])

      self.broadcast(msg,filenos)

  def broadcast(self, msg, filenos):
    msg = json.dumps(msg)
    for fileno in filenos:
      self.connections[fileno].sendMessage(msg)

  def addUserConnection(self, username, fileno):
    if not self.users.has_key(username):
      user = User(username)
      self.users[username] = user
    if self.connection_to_user.has_key(fileno):
      print "Stale fileno?"
      #TODO: set up exception for weird states
    else:
      self.connection_to_user[fileno] = username

    if not self.user_to_connections.has_key(username):
      self.user_to_connections[username] = set()
    self.user_to_connections[username].add(fileno)

  


# dictionary keyed by username
class User(object):
  def __init__(self, name):
    self.name = name
    self.filenos = []
  def addConnection(self, connection):
    self.filenos.append(connection.fileno) 

# dictionary keyed by fileno
class Connection(object):
  def __init__(self, connection, owner):
    self.connection    = connection
    self.authenticated = False

# dictionary keyed by channel name
class Channel(object):
  def __init__(self, channel, owner):
    self.name          = channel
    self.owner         = owner 

# WebSocket implementation
class WebSocket(object):

  handshake = (
    "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
    "Upgrade: WebSocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Accept: %(acceptstring)s\r\n"
    "Server: TestTest\r\n"
    "Access-Control-Allow-Origin: http://localhost\r\n"
    "Access-Control-Allow-Credentials: true\r\n"
    "\r\n"
  )


  # Constructor
  def __init__(self, client, server):
    self.client = client
    self.server = server
    self.handshaken = False
    self.header = ""
    self.data = ""


  # Serve this client
  def decode(self, data):

    # If we haven't handshaken yet
    if not self.handshaken:
      logging.debug("No handshake yet")
      self.header += data
      if self.header.find('\r\n\r\n') != -1:
        parts = self.header.split('\r\n\r\n', 1)
        self.header = parts[0]
        if self.dohandshake(self.header, parts[1]):
          logging.info("Handshake successful")
          self.handshaken = True
      return None

    # We have handshaken
    else:
      logging.debug("Handshake is complete")
      
      # Decode the data that we received according to section 5 of RFC6455
      recv = self.decodeCharArray(data)
      print "-->" + str(recv) + "<--" 
      # Send our reply
      return ''.join(recv).strip()


  # Stolen from http://www.cs.rpi.edu/~goldsd/docs/spring2012-csci4220/websocket-py.txt
  def sendMessage(self, s):
    """
    Encode and send a WebSocket message
    """

    # Empty message to start with
    message = ""
    
    # always send an entire message as one frame (fin)
    b1 = 0x80

    # in Python 2, strs are bytes and unicodes are strings
    if type(s) == unicode:
      b1 |= TEXT
      payload = s.encode("UTF8")
        
    elif type(s) == str:
      b1 |= TEXT
      payload = s

    # Append 'FIN' flag to the message
    message += chr(b1)

    # never mask frames from the server to the client
    b2 = 0
    
    # How long is our payload?
    length = len(payload)
    if length < 126:
      b2 |= length
      message += chr(b2)
    
    elif length < (2 ** 16) - 1:
      b2 |= 126
      message += chr(b2)
      l = struct.pack(">H", length)
      message += l
    
    else:
      l = struct.pack(">Q", length)
      b2 |= 127
      message += chr(b2)
      message += l

    # Append payload to message
    message += payload

    # Send to the client
    self.client.send(str(message))


  # Stolen from http://stackoverflow.com/questions/8125507/how-can-i-send-and-receive-websocket-messages-on-the-server-side
  def decodeCharArray(self, stringStreamIn):
  
    # Turn string values into opererable numeric byte values
    byteArray = [ord(character) for character in stringStreamIn]
    datalength = byteArray[1] & 127
    indexFirstMask = 2

    if datalength == 126:
      indexFirstMask = 4
    elif datalength == 127:
      indexFirstMask = 10

    # Extract masks
    masks = [m for m in byteArray[indexFirstMask : indexFirstMask+4]]
    indexFirstDataByte = indexFirstMask + 4
    
    # List of decoded characters
    decodedChars = []
    i = indexFirstDataByte
    j = 0
    
    # Loop through each byte that was received
    while i < len(byteArray):
    
      # Unmask this byte and add to the decoded buffer
      decodedChars.append( chr(byteArray[i] ^ masks[j % 4]) )
      i += 1
      j += 1

    # Return the decoded string
    return decodedChars


  # Handshake with this client
  def dohandshake(self, header, key=None):
  
    logging.debug("Begin handshake: %s" % header)
    
    # Get the handshake template
    handshake = self.handshake
    
    # Step through each header
    for line in header.split('\r\n')[1:]:
      name, value = line.split(': ', 1)
      
      # If this is the key
      if name.lower() == "sec-websocket-key":
    
        # Append the standard GUID and get digest
        combined = value + MAGIC_GUID
        response = base64.b64encode(hashlib.sha1(combined).digest())
        
        # Replace the placeholder in the handshake response
        handshake = handshake % { 'acceptstring' : response }

    logging.debug("Sending handshake %s" % handshake)
    self.client.send(handshake)
    return True

  def onmessage(self, data):
    #logging.info("Got message: %s" % data)
    self.send(data)

  def send(self, data):
    logging.info("Sent message: %s" % data)
    self.client.send("\x00%s\xff" % data)

  def close(self):
    self.client.close()
 
 
 
# Entry point
if __name__ == "__main__":
 
  logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
  server = ChatServer("", 8000, WebSocket)
  server_thread = Thread(target=server.listen, args=[5])
  server_thread.start()

  # Add SIGINT handler for killing the threads
  def signal_handler(signal, frame):
    logging.info("Caught Ctrl+C, shutting down...")
    server.running = False
    sys.exit()
  signal.signal(signal.SIGINT, signal_handler)

  while True:
    time.sleep(100)
