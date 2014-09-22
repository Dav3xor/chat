import redis, json
from passlib.apps import custom_app_context as pwd_context


class RedisServer(object):
  def __init__(self, host='localhost', port=6379, db=0, keystart="chat"):
    self.redis = redis.StrictRedis(host, port, db)
    self.keystart = keystart

  def make_key(self,keytype,key):
    return self.keystart+'-'+keytype+'-'+key

  def user_exists(self, username):
    # TODO: maybe cache users to reduce round trips to server?
    return self.redis.exists(self.make_key('user', username))
    
  def authenticate(self, username, password):
    user_key = self.make_key('user',username)
   
    json_user = self.redis.get(user_key)
    if not json_user:
      return False

    try:
      user = json.loads(json_user)
    except ValueError,TypeError:
      return False

    if 'pwhash' not in user:
      return False

    if pwd_context.verify(password, user['pwhash']):
      return user
    else:
      return False

  def new_user(self, username, password):
    user_key = self.make_key('user',username)

    # user already exists
    if self.redis.exists(user_key):
      return False
    user = { 'pwhash': pwd_context.encrypt(password) }
    self.redis.set(user_key, json.dumps(user))
    return user
  
