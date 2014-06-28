import pylws

listener = pylws.WebSocket('127.0.0.1', 8000,
                           '/home/dave/blah.cert',
                           '/home/dave/blah.key', 
                           {'/': '/home/dave/chat/server.py'})

class protocol_handler(object):
  def new_connection(self, ws, fd, protocol):
    print "(python) new connection!"
  def closed_connection(self, ws, fd, protocol):
    print "(python) closed connection"
  def recieve_data(self, ws, fd, protocol, msg):
    print "(python) new data -- %s" % msg
    #ws.write(fd,"hello");

handler = protocol_handler()

listener.register_protocol('local_echo', handler)
listener.listen()
while 1:
  listener.run(100)
