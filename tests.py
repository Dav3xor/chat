import chatserver
import unittest

class WSStub(object):
  def __init__(self):
    self.history = []
  def write(self,filenos,msg):
    self.history = [filenos, msg] 
    return str(filenos) + ' - ' + msg

class TestInit(unittest.TestCase):
  def test_init(self):
    handler = chatserver.chat_handler()
    self.assertEqual(handler.connection_to_user,{})
    self.assertEqual(handler.user_to_connections,{})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.channel_to_users,{})

class TestAuthenticate(unittest.TestCase):
  def test_authenticate(self):
    ws = WSStub()
    handler = chatserver.chat_handler()

    # failed password...
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'Dav3xor',
                                               'pass':'flasfdlj'},1),
                     False)
    self.assertEqual(handler.connection_to_user,{})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.user_to_connections,{})

    # failed username
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'Dav3xorx',
                                               'pass':'password'},1),
                     False)
    self.assertEqual(handler.connection_to_user,{})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.user_to_connections,{})

    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'Dav3xor',
                                               'pass':'password'},1),
                     True)
    self.assertEqual(handler.connection_to_user,{1: 'Dav3xor'})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.channel_to_users,{})
    self.assertEqual(handler.user_to_connections,{'Dav3xor': set([1])})
    
    # put the user in a channel so we can test changing users. 
    handler.join(ws, {'mtype': 'join', 'channel': 'channel'}, 1)
    self.assertEqual(handler.user_to_channels,{'Dav3xor': set(['channel'])})
    self.assertEqual(handler.channel_to_users,{'channel': set(['Dav3xor'])})


    # test changing users 
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'User',
                                               'pass':'x'},1),
                     True)
    self.assertEqual(handler.connection_to_user,{1: 'User'})
    self.assertEqual(handler.user_to_connections,{'User': set([1])})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.channel_to_users,{})

    # test 2 users at once...
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'Dav3xor',
                                               'pass':'password'},2),
                     True)
    self.assertEqual(handler.connection_to_user,{1: 'User', 2: 'Dav3xor'})
    self.assertEqual(handler.user_to_connections,{'Dav3xor': set([2]), 'User': set([1])})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.channel_to_users,{})

class TestJoin(unittest.TestCase):
  def test_join(self):
    ws = WSStub()
    handler = chatserver.chat_handler()
    
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'User',
                                               'pass':'x'},1),
                     True)
    self.assertEqual(handler.connection_to_user,{1: 'User'})
    self.assertEqual(handler.user_to_connections,{'User': set([1])})
    self.assertEqual(handler.user_to_channels,{})
    self.assertEqual(handler.channel_to_users,{})
   
    self.assertEqual(handler.join(ws, {'mtype': 'join', 'channel': 'channel1'}, 1), True)
    self.assertEqual(handler.connection_to_user,{1: 'User'})
    self.assertEqual(handler.user_to_connections,{'User': set([1])})
    self.assertEqual(handler.user_to_channels,{'User': set(['channel1'])})
    self.assertEqual(handler.channel_to_users,{'channel1': set(['User'])})
   
    # make sure we're graceful if the user isn't logged in 
    self.assertEqual(handler.join(ws, {'mtype': 'join', 'channel': 'channel2'}, 2), False)
    self.assertEqual(handler.connection_to_user,{1: 'User'})
    self.assertEqual(handler.user_to_connections,{'User': set([1])})
    self.assertEqual(handler.user_to_channels,{'User': set(['channel1'])})
    self.assertEqual(handler.channel_to_users,{'channel1': set(['User'])})
  
    # log in a second user... 
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'Dav3xor',
                                               'pass':'password'},2),
                     True)
    self.assertEqual(handler.connection_to_user,{1: 'User', 2: 'Dav3xor'})
    self.assertEqual(handler.user_to_connections,{'Dav3xor': set([2]), 'User': set([1])})
    self.assertEqual(handler.user_to_channels,{'User': set(['channel1'])})
    self.assertEqual(handler.channel_to_users,{'channel1': set(['User'])})

    # User logs into a second channel 
    self.assertEqual(handler.join(ws, {'mtype': 'join', 'channel': 'channel2'}, 1), True)
    self.assertEqual(handler.connection_to_user,{1: 'User', 2: 'Dav3xor'})
    self.assertEqual(handler.user_to_connections,{'Dav3xor': set([2]), 'User': set([1])})
    self.assertEqual(handler.user_to_channels,{'User': set(['channel1', 'channel2'])})
    self.assertEqual(handler.channel_to_users,{'channel2': set(['User']), 'channel1': set(['User'])})

    # Dav3xor logs into the same channel
    self.assertEqual(handler.join(ws, {'mtype': 'join', 'channel': 'channel2'}, 2), True)
    self.assertEqual(handler.connection_to_user,{1: 'User', 2: 'Dav3xor'})
    self.assertEqual(handler.user_to_connections,{'Dav3xor': set([2]), 'User': set([1])})
    self.assertEqual(handler.user_to_channels,{'Dav3xor': set(['channel2']), 
                                               'User': set(['channel1', 'channel2'])})
    self.assertEqual(handler.channel_to_users,{'channel2': set(['User', 'Dav3xor']), 'channel1': set(['User'])})

class TestMessage(unittest.TestCase):
  def testmessage(self):
    ws = WSStub()
    handler = chatserver.chat_handler()
   
    # try to send a message with no user or fileno.. 
    self.assertEqual(handler.message(ws, {'mtype': 'msg', 'to': 'Dav3stown', 'msg':'Hello World'},1), 
                     False)

    # log in a user... 
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'User',
                                               'pass':'x'},1),
                     True)

    # try to send a message to a channel the user hasn't joined
    self.assertEqual(handler.message(ws, {'mtype': 'msg', 'to': 'Dav3stown', 'msg':'Hello World'},1), 
                     False)

    # join user to a channel
    self.assertEqual(handler.join(ws, {'mtype': 'join', 
                                       'channel': 'channel1'}, 
                                  1), 
                     True)
    self.assertEqual(handler.connection_to_user,{1: 'User'})
    self.assertEqual(handler.user_to_connections,{'User': set([1])})
    self.assertEqual(handler.user_to_channels,{'User': set(['channel1'])})
    self.assertEqual(handler.channel_to_users,{'channel1': set(['User'])})
    
    # actually send a message to a channel the user is joined to...
    self.assertEqual(handler.message(ws, {'mtype': 'msg', 
                                          'to': 'channel1', 
                                          'msg':'Hello World'},
                                     1), 
                     True)
    self.assertEqual(ws.history, [[1],
                                  '{"mtype": "msg", ' +
                                  '"to": "channel1", ' +
                                  '"from": "User", ' +
                                  '"msg": "Hello World"}'])

    # add a second user 
    self.assertEqual(handler.authenticate(ws, {'mtype': 'auth', 
                                               'user':'Dav3xor',
                                               'pass':'password'},2),
                     True)

    # send a message to the channel before the second user joins
    self.assertEqual(handler.message(ws, {'mtype': 'msg', 
                                          'to': 'channel1', 
                                          'msg':'Hello World2'},1), 
                     True)
    self.assertEqual(ws.history, [[1],
                                  '{"mtype": "msg", ' +
                                  '"to": "channel1", ' +
                                  '"from": "User", ' +
                                  '"msg": "Hello World2"}'])




    # send a message to the channel after the second user joins
    self.assertEqual(handler.join(ws, {'mtype': 'join', 
                                       'channel': 'channel1'}, 
                                  2), 
                     True)
    self.assertEqual(handler.message(ws, {'mtype': 'msg', 
                                          'to': 'channel1', 
                                          'msg':'Hello World3'},
                                     1), 
                     True)
    self.assertEqual(ws.history, [[1,2],
                                  '{"mtype": "msg", ' +
                                  '"to": "channel1", ' +
                                  '"from": "User", ' +
                                  '"msg": "Hello World3"}'])

    

class TestBroadcast(unittest.TestCase):
  def test_broadcast(self):
    ws = WSStub()
    handler = chatserver.chat_handler()
    self.assertEqual(handler.broadcast(ws, '"test"', [1,2]), 
                     '[1, 2] - "\\"test\\""') 

    self.assertRaises(TypeError, handler.broadcast, ws, set('test'), [1,2])