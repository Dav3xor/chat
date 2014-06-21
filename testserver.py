import pylws

print "1"
listener = pylws.WebSocket('127.0.0.1', 8000,
                           '/home/dave/blah.cert',
                           '/home/dave/blah.key', 
                           {'/': '/home/dave/chat/server.py'})


def handler(ws, fd, protocol, msg):
  ws.write(fd,"hello");
  #print msg

print "2"
listener.register('local_echo', handler)
print "3"
listener.listen()
print "4"
while 1:
  listener.run(100)
print "5"
