

function MegaChataTron(hostname)
{
  this.username = '';
  this.STATE_DISCONNECTED     = 1;
  this.STATE_CONNECTING       = 2;
  this.STATE_CONNECTED        = 4;
  this.state                  = this.STATE_DISCONNECTED;
  this.msgs                   = []; 
  this.authenticated          = false;
  
  // functions you need to add to MegaChataTron:
  // handleMessage(channel,msg)
  // handleAuthenticated(channels)

  this.login   = function(username, password) {
    if(this.state === this.STATE_DISCONNECTED){
      this.connect();
    }
    var msg = {'type': 'auth', 
               'user': username, 
               'pass': password};
    this.sendMessage(msg);
  }

  this.emptyQueue  = function() {
    var nextmsg;
    while(this.msgs.length) {
      // TODO: stop sending if connection goes down...
      nextmsg = this.msgs.shift();
      this.connection.send(JSON.stringify(nextmsg));
    }
  }
 
  this.sendMessage = function(msg) {
    if((this.state === this.STATE_CONNECTED)||
       (this.state === this.STATE_AUTHENTICATED)) {
      if(this.msgs.length > 0) {
        this.emptyQueue();
      }
      this.connection.send(JSON.parse(msg));
    } else {
      this.msgs.unshift(msg);
    }
  }
      
  this.onOpen = function () {
    this.state = this.STATE_CONNECTED;
    this.emptyQueue();     
  }

  var obj = this; 
  this.connect = function() {
    this.connection           = new WebSocket(hostname,'chat');

    this.connection.onopen    = function(){obj.onOpen()};

    this.connection.onerror   = function (error) {
      alert('error: ' + error);
    }
    this.connection.onmessage = function (e) {
      var msg = JSON.parse(e.data);
      
      alert('recieved: '+ e.data);
    }
    this.state                = this.STATE_CONNECTING;
  }
}

$(document).ready(function () {
  $('[data-toggle="offcanvas"]').click(function () {
    $('.row-offcanvas').toggleClass('active')
  });
});
