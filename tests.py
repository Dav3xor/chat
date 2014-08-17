import chatserver
import unittest

class WSStub(object):
  def write(self,filenos,msg):
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
class TestBroadcast(unittest.TestCase):
  def test_broadcast(self):
    ws = WSStub()
    handler = chatserver.chat_handler()
    self.assertEqual(handler.broadcast(ws, '"test"', [1,2]), 
                     '[1, 2] - "\\"test\\""') 

    self.assertRaises(TypeError, handler.broadcast, ws, set('test'), [1,2])
