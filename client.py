from ws4py.client.threadedclient import WebSocketClient

class DummyClient(WebSocketClient):
    def opened(self):
        def data_provider():
            for i in xrange(1000000000):
                yield "#"

        self.send(data_provider())

        for i in range(0, 200, 1):
            #print i
            self.send("*" * i)

    def closed(self, code, reason=None):
        print "Closed down", code, reason

    def received_message(self, m):
        print m
        if len(m) == 10:
            print "closing"
            self.close(reason='Bye bye')
        print "not closing"


def do_test():
  wses = []
  for i in xrange(1000):
    ws = DummyClient('ws://localhost:8000/', protocols=['local_echo'])
    ws.connect()
    connections.append(ws)
    #ws.run_forever()
    wses.append(ws)
  for i in wses:
    i.close()

if __name__ == '__main__':
    connections = []
    for j in xrange(1000):
      do_test()  
    #connections[0].run_forever()
