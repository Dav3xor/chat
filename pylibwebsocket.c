#include <stdio.h>
#include <stdlib.h>
#include <libwebsockets.h>
#include <stdbool.h>
#include <Python.h>
#include <structmember.h>
/* PYTHON OBJECTS:
   borrowed == you don't have control of it, DON'T DECREF, DON'T RETURN IT
   new      == you have control, DECREF it, or RETURN IT.
*/

typedef struct {
  PyObject_HEAD
  /* Type-specific fields go here. */
  struct       lws_context_creation_info info;
  unsigned int numprotocols;
  struct       libwebsocket_context      *context;
  struct       libwebsocket_protocols    *protocols;
               PyObject                  *dispatch;
               PyObject                  *deque;
               PyObject                  *queues;
               PyObject                  *urls;
               PyObject                  *connections;
} WebSocketObject;

void init_protocol(struct libwebsocket_protocols *protocol){
  memset((void *)protocol, 0, sizeof(struct libwebsocket_protocols));
}

void repr(PyObject *obj){
  if(!obj) {
    printf("obj = NULL\n");
  }
  Py_INCREF(obj);
  PyObject *repr = PyObject_Repr(obj);
  if(!repr){
    printf("fuck!\n");
  } else {
    const char* s = PyString_AsString(repr);
    printf("repr = %s\n",s);
    //Py_DECREF(repr);
  }
  Py_DECREF(obj);
}

static PyObject * WebSocket_write (WebSocketObject *self, PyObject *args)
{

  PyObject      *fds;
  PyObject      *msg;
  int            numfds;
  PyObject      *key;
  struct         libwebsocket *writelws;
  unsigned int   i;

  if (!( PyArg_ParseTuple(args, "OO", &fds, &msg))) {
    return NULL;
  }
 
  numfds = PySequence_Length(fds);
  if(numfds == -1){
    printf("not a sequence\n");
    return NULL;
  }
 
  for (i=0; i<numfds; i++) {
    key = PySequence_GetItem(fds, i);
    if (key) {
      PyObject *pyconn = PyDict_GetItem(self->connections, key); // borrowed reference
      writelws = (struct libwebsocket *)PyCObject_AsVoidPtr(pyconn);
      PyObject *queue  = PyDict_GetItem(self->queues, key);
      if ((pyconn) && (queue) && (msg) && (writelws) &&
          (PyObject_TypeCheck(msg, &PyString_Type))) {
        PyObject_CallMethod(queue, "append", "(O)", msg);
        libwebsocket_callback_on_writable(self->context,writelws);
      }
      Py_DECREF(key);
    }
  }

  Py_RETURN_NONE;

}


static PyObject * WebSocket_run (WebSocketObject *self, PyObject *args)
{
  if ((self->context) ) {
    int wait_time;
    if ( PyArg_ParseTuple(args, "i", &wait_time)) {
      libwebsocket_service(self->context, wait_time);
    }
  }
 
  Py_RETURN_NONE;
}


static int WebSocket_dispatch (struct libwebsocket_context * this,
                               struct libwebsocket *wsi,
                               enum libwebsocket_callback_reasons reason,
                               void *user,
                               void *in,
                               size_t len)
{
    const struct libwebsocket_protocols *cur_protocol;
    WebSocketObject *self=libwebsocket_context_user(this);
    
    int fd = -1;
    
    if(wsi) {
      fd = libwebsocket_get_socket_fd(wsi);
    }

    if(!self) {
      printf("user pointer not initialized\n");
    }

    // reason for callback
    switch (reason) {

        case LWS_CALLBACK_ESTABLISHED: {
            cur_protocol = libwebsockets_get_protocol (wsi);
            if (!(cur_protocol)) {
              printf ("couldn't get protocol?\n");
              return -1;
            }  
             
            PyObject *connection = PyCObject_FromVoidPtr(wsi, NULL);            // new reference
            PyObject *newqueue = NULL;

            if (!connection) {
              printf ("can't allocate new python connection reference\n");
              return -1;
            }
            PyObject *key = PyInt_FromLong(fd);                                 // new reference

            if (!key) {
              printf ("cannot allocate python connection key\n");
              return -1;
            }

            if (self->deque) {

              newqueue = PyObject_CallFunction(self->deque,"()");
              if(!newqueue) {
                printf("newqueue fail\n");
                return -1;
              }
            }



            PyDict_SetItem(self->connections, key, connection);
            PyDict_SetItem(self->queues, key, newqueue); 

            PyObject *handler = PyDict_GetItemString(self->dispatch,
                                                     cur_protocol->name); // borrowed reference
            if(handler) {
              PyObject_CallMethod(handler, "new_connection", "Ois", 
                                self, fd, cur_protocol->name);
            }            
            Py_DECREF(key);
            Py_DECREF(connection);
            printf("connection established\n");
            break;
        }

        case LWS_CALLBACK_RECEIVE: {
            cur_protocol = libwebsockets_get_protocol (wsi);
            if (!(cur_protocol)) {
              printf ("couldn't get protocol?\n");
              return -1;
            } 

            PyObject *handler = PyDict_GetItemString(self->dispatch,
                                                     cur_protocol->name); // borrowed reference
            
            if(handler) {
              PyObject_CallMethod(handler, "recieve_data", "Oiss",  
                                self, fd, cur_protocol->name, in);
            }
            break;
        }
        
        case LWS_CALLBACK_SERVER_WRITEABLE: {
            PyObject    *queue;
            PyObject    *output;
            Py_ssize_t   queuelen;
            char        *outputstr;
            Py_ssize_t   outputlen;
            
            int          fd          = libwebsocket_get_socket_fd(wsi);
            PyObject    *key         = PyInt_FromLong(fd);  // new reference

            if(key) {
              queue = PyDict_GetItem(self->queues, key);
              if(queue){
                queuelen = PySequence_Length(queue);
                if(queuelen){
                  output = PyObject_CallMethod(queue, "popleft", "()");            // new reference
                  if ((output) && (PyObject_TypeCheck(output, &PyString_Type))) {
                    PyString_AsStringAndSize(output,&outputstr,&outputlen);
                    if ((outputstr)&&(outputlen)) {
                      char *buffered = malloc(LWS_SEND_BUFFER_PRE_PADDING + 
                                              outputlen + 
                                              LWS_SEND_BUFFER_POST_PADDING);
                      strncpy(&buffered[LWS_SEND_BUFFER_PRE_PADDING],
                              outputstr,
                              outputlen+1);

                      libwebsocket_write(wsi, 
                                         (unsigned char *)&buffered[LWS_SEND_BUFFER_PRE_PADDING], 
                                         outputlen, LWS_WRITE_TEXT);
                      free(buffered);
                    }
                    Py_DECREF(output);
                  }
                  if(queuelen - 1 > 0) {
                    libwebsocket_callback_on_writable(self->context,wsi);
                  } 
                }
              }
              Py_DECREF(key);
            }
            break;
        }
            
        case LWS_CALLBACK_CLOSED: {
            cur_protocol = libwebsockets_get_protocol (wsi);                              
            if (!(cur_protocol)) {
              printf ("couldn't get protocol?\n");
              return -1;
            }
            PyObject *handler = PyDict_GetItemString(self->dispatch,
                                                     cur_protocol->name);  // borrowed reference
            int fd = libwebsocket_get_socket_fd(wsi);
            PyObject *key = PyInt_FromLong(fd);                            // new reference
            if ((handler) && (cur_protocol->name)) {
              PyObject_CallMethod(handler, "closed_connection", "Ois", 
                                self, fd, cur_protocol->name);
            }            
            PyDict_DelItem(self->connections, key);
            PyDict_DelItem(self->queues, key);
            Py_DECREF(key);
            printf("connection dropped (%d)\n",fd);
            break;
        }
    }
    return 0;
}

static int WebSocket_http_callback(struct libwebsocket_context *context,
                                   struct libwebsocket *wsi,
                                   enum libwebsocket_callback_reasons reason, void *user,
                                   void *in, size_t len)
{
    WebSocketObject *self=libwebsocket_context_user(context);
    int return_value = 0; 
    switch (reason) {
        // http://git.warmcat.com/cgi-bin/cgit/libwebsockets/tree/lib/libwebsockets.h#n260
        case LWS_CALLBACK_CLIENT_WRITEABLE:
            printf("connection established\n");
            
        // http://git.warmcat.com/cgi-bin/cgit/libwebsockets/tree/lib/libwebsockets.h#n281
        case LWS_CALLBACK_HTTP: {
            char *requested_uri = (char *) in;
            printf("requested URI: %s\n", requested_uri);
           
            PyObject *pyfile = PyDict_GetItemString(self->urls, 
                                                    requested_uri); // borrowed reference
            if(pyfile && PyObject_TypeCheck(pyfile, &PyString_Type)) {
                char *file      = PyString_AsString(pyfile);   
                printf("on disk: %s\n", file);
                char *extension = strrchr(requested_uri, '.');
                char *mime;
                
                // choose mime type based on the file extension
                if (extension == NULL) {
                    mime = "text/plain";
                } else if (strcmp(extension, ".png") == 0) {
                    mime = "image/png";
                } else if (strcmp(extension, ".jpg") == 0) {
                    mime = "image/jpg";
                } else if (strcmp(extension, ".gif") == 0) {
                    mime = "image/gif";
                } else if (strcmp(extension, ".html") == 0) {
                    mime = "text/html";
                } else if (strcmp(extension, ".css") == 0) {
                    mime = "text/css";
                } else {
                    mime = "text/plain";
                }
                
                // by default non existing resources return code 400
                // for more information how this function handles headers
                // see it's source code
                // http://git.warmcat.com/cgi-bin/cgit/libwebsockets/tree/lib/parsers.c#n1896
                libwebsockets_serve_http_file(context, wsi, file, mime, NULL);
            } else {
              printf("can't find: %s\n", file);
            }
            
            // close connection
            return_value = -1;
            break;
        }
        default:
            //printf("unhandled callback\n");
            break;
    }
    
    return return_value;
}
 



static int WebSocket_init(WebSocketObject *self, 
                          PyObject *args)
{
  int        port;
  char      *interface;
  char      *cert_path;
  char      *key_path;
  PyObject  *urls;
  PyObject  *collections;
  PyObject  *protocols;
  if (! PyArg_ParseTuple(args, "sissOO", 
                         &interface, &port,
                         &cert_path, &key_path, &protocols, &urls)) {
    return -1;
  }

  collections   = PyImport_ImportModule("collections");       // new reference
  if(collections) {
    self->deque = PyObject_GetAttrString(collections, "deque"); // new reference
    if(!(self->deque)) {
      return -1;
    }
    Py_DECREF(collections);
  }
  self->dispatch                      = PyDict_New();           // new reference
  self->connections                   = PyDict_New();           // new reference;
  self->queues                        = PyDict_New();           // new reference;
  self->urls                          = urls;
  if(!(self->dispatch || self->connections || self->queues)) {
    return -1;
  }
  
  if (PyDict_Check(protocols)) {
    Py_ssize_t numprotocols = PyDict_Size(protocols);
    Py_ssize_t pos          = 0;
    PyObject   *key;
    PyObject   *value;
  
  
    // add 1 for http and 1 for the sentinel...
    self->protocols = malloc(sizeof(struct libwebsocket_protocols)*(numprotocols+2));
    self->numprotocols = 1;
    if(!self->protocols) {
      printf("Could not initialize protocols\n");
      return -1;
    } else {
      init_protocol(&self->protocols[0]);
      self->protocols[0].name                  = "http-only";
      self->protocols[0].callback              = WebSocket_http_callback;
      self->protocols[0].per_session_data_size = 0;

      while (PyDict_Next(protocols, &pos, &key, &value)) {
        init_protocol(&self->protocols[self->numprotocols]);
        if(!(PyString_Check(key))) {
          continue;
        } 
        Py_ssize_t namelen = PyString_Size(key);
        char *namestr = malloc(namelen+1);
        if(!namestr){
          return -1;
        }
        strncpy(namestr,PyString_AsString(key), namelen+1);
       
        
        init_protocol(&self->protocols[self->numprotocols]);
        self->protocols[self->numprotocols].name                  = namestr;
        self->protocols[self->numprotocols].callback              = WebSocket_dispatch;
        self->protocols[self->numprotocols].per_session_data_size = 0;
        PyDict_SetItem(self->dispatch, key, value);        // increments key and value references
        self->numprotocols += 1;
      } 
      self->protocols[self->numprotocols].name                  = NULL;
      self->protocols[self->numprotocols].callback              = NULL;
      self->protocols[self->numprotocols].per_session_data_size = 0;
    }
  } else {
    printf("protocols weird?\n");
  }

  self->info.port                     = port;
  self->info.iface                    = interface;
  self->info.protocols                = self->protocols;
  self->info.extensions               = NULL;
  self->info.ssl_cert_filepath        = NULL;  //cert_path;
  self->info.ssl_private_key_filepath = NULL;  //key_path;
  self->info.options                  = 0; 
  self->info.user                     = (void *)self;
  self->context                       = libwebsocket_create_context (&self->info);
  return 0;
}

static void WebSocket_dealloc(WebSocketObject *self)
{ 
  //libwebsocket_context_destroy(self->context);
  for (int i=1; i<self->numprotocols; i++) {
    free((void *)self->protocols[i].name);
  }
  free(self->protocols);
  Py_DECREF(self->dispatch);
  Py_DECREF(self->deque);
  Py_DECREF(self->queues);
  Py_DECREF(self->urls);
  Py_DECREF(self->connections);
  self->ob_type->tp_free((PyObject*)self);
}


static PyMemberDef WebSocket_members[] = {
    {"queues", T_OBJECT_EX, offsetof(WebSocketObject, queues), 0,
     "message queues"},
    {NULL}  /* Sentinel */
};

static PyMethodDef WebSocket_methods[] = {
  {"run", (PyCFunction)WebSocket_run, METH_VARARGS,
   "Run websocket server (for n milliseconds)"
  },
  {"write", (PyCFunction)WebSocket_write, METH_VARARGS,
   "tell lib websockets to write to a socket"
  },
  {NULL}  /* Sentinel */
};


static PyTypeObject WebSocketType = {
  PyObject_HEAD_INIT(NULL)
  0,                         /*ob_size*/
  "pylws.WebSocket",  /*tp_name*/
  sizeof(WebSocketObject), /*tp_basicsize*/
  0,                         /*tp_itemsize*/
  (destructor)WebSocket_dealloc, /*tp_dealloc*/
  0,                         /*tp_print*/
  0,                         /*tp_getattr*/
  0,                         /*tp_setattr*/
  0,                         /*tp_compare*/
  0,                         /*tp_repr*/
  0,                         /*tp_as_number*/
  0,                         /*tp_as_sequence*/
  0,                         /*tp_as_mapping*/
  0,                         /*tp_hash */
  0,                         /*tp_call*/
  0,                         /*tp_str*/
  0,                         /*tp_getattro*/
  0,                         /*tp_setattro*/
  0,                         /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT,        /*tp_flags*/
  "pylws is a Python wrapper for the C libwebsockets library.\n",
  0,                         /* tp_traverse */
  0,                         /* tp_clear */
  0,                         /* tp_richcompare */
  0,                         /* tp_weaklistoffset */
  0,                         /* tp_iter */
  0,                         /* tp_iternext */
  WebSocket_methods,         /* tp_methods */
  WebSocket_members,         /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)WebSocket_init,  /* tp_init */
  0,                         /* tp_alloc */
  0,              /* tp_new */
};


#ifndef PyMODINIT_FUNC  /* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initpylws(void) 
{
  PyObject* m;

  WebSocketType.tp_new = PyType_GenericNew;
  if (PyType_Ready(&WebSocketType) < 0)
    return;

  m = Py_InitModule3("pylws", WebSocket_methods,
                     "A python wrapper for the C libwebsockets library");

  Py_INCREF(&WebSocketType);
  PyModule_AddObject(m, "WebSocket", (PyObject *)&WebSocketType);
}
