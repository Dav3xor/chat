import redis
from passlib.apps import custom_app_context as pwd_context


class RedisServer(object):
  def __init__(self, host='localhost', port=6379, db=0, keystart="chat"):
    self.redis = redis.StrictRedis(host, port, db)
    self.keystart = keystart

  def make_key(self,keytype,key):
    return self.keystart+'-'+keytype+'-'+key

  def authenticate(self, username, password):
    user_key = self.make_key(user,username)
   
    json_user = self.redis.get(user_key)
    if not json_user:
      return False

    try:
      user = json.loads(json_user)
    except TypeError:
      return False

    if pwd_context.verify(password, user['pwhash']):
      return user
    else:
      return False

  """
  def add_user(self, username, password):
    userkey = self.keystart+'user-'+username
    if self.redis.exists('chat-user-'
  """
