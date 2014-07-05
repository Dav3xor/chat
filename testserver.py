import pylws
import random
from pprint import pprint

class protocol_handler(object):
  def new_connection(self, ws, fd, protocol):
    print "(python) new connection!"
    """
    print "ws="+str(ws)
    print "fd="+str(fd)
    print "protocol="+str(protocol)
    """
  def closed_connection(self, ws, fd, protocol):
    print "(python) closed connection"
    """
    print "ws="+str(ws)
    print "fd="+str(fd)
    print "protocol="+str(protocol)
    """
  def recieve_data(self, ws, fd, protocol, msg):
    #print "(python) new data -- %s" % msg
    print "x",
    """
    print "ws="+str(ws)
    print "fd="+str(fd)
    print "protocol="+str(protocol)
    """
    #msglen = random.randint(1,100)
    ws.write((fd,),"hello")


handler = protocol_handler()

listener = pylws.WebSocket('127.0.0.1', 8000,
                           '/home/dave/blah.cert',
                           '/home/dave/blah.key', 
                           {'local_echo': handler},
                           {'/': '/home/dave/chat/server.py'})
while 1:
  listener.run(100)
