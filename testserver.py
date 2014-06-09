import pylws

listener = pylws.WebSocket('127.0.0.1', 8000,
                           '/home/dave/blah.cert',
                           '/home/dave/blah.key')


def handler(protocol, msg):
  print msg

listener.register('local_echo', handler)
listener.listen()
listern.run(10)
