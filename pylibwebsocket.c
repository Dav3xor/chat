#include <stdio.h>
#include <stdlib.h>
#include <libwebsockets.h>
#include <stdbool.h>
#include <Python.h>

typedef struct {
  PyObject_HEAD
  /* Type-specific fields go here. */
  struct       libwebsocket_context      *context;
  struct       libwebsocket_protocols    *protocols;
               PyObject                  *dispatch;
               PyObject                  *urls;
               PyObject                  *connections;
  struct       lws_context_creation_info info;
  unsigned int numprotocols;
  bool         running; 
} WebSocketObject;



static PyObject * WebSocket_listen (WebSocketObject *self, PyObject *args)
{
  if(self->context) {
    //libwebsocket_context_destroy(self->context);
  }

  self->context = libwebsocket_create_context (&self->info);
  self->running = true;
  Py_RETURN_NONE;

}

static PyObject * WebSocket_run (WebSocketObject *self, PyObject *args)
{
  if ((self->context) && (self->running)) {
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
    if(!self) {
      printf("user pointer not initialized\n");
    }

    // reason for callback
    switch (reason) {

        case LWS_CALLBACK_ESTABLISHED: {
            int fd = libwebsocket_get_socket_fd(wsi);

            PyObject *connection = PyCObject_FromVoidPtr(wsi, NULL);
            if (!connection) {
              printf ("can't allocate new python connection reference\n");
              return -1;
            }
            PyObject *key = PyInt_FromLong(fd);

            if (!key) {
              printf ("cannot allocate python connection key\n");
              return -1;
            }

            PyDict_SetItem(self->connections, key, connection);
            Py_DECREF(key);
            Py_DECREF(connection);
            printf("connection established\n");
            break;
        }

        case LWS_CALLBACK_RECEIVE: {
            cur_protocol = libwebsockets_get_protocol (wsi);
            PyObject *callback = PyDict_GetItemString(self->dispatch,cur_protocol->name);
            if(callback) {
              PyObject_CallFunction(callback, "ss", cur_protocol, in);
            }            
            printf("received data: %s\n", (char *) in);
            break;
        }
        case LWS_CALLBACK_CLOSED: {
              int fd = libwebsocket_get_socket_fd(wsi);
              PyObject *key = PyInt_FromLong(fd);
              PyDict_DelItem(self->connections, key);
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
           
            PyObject *pyfile = PyDict_GetItemString(self->urls, requested_uri);
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
  printf("a\n");
  if (! PyArg_ParseTuple(args, "sissO", 
                         &interface, &port,
                         &cert_path, &key_path, &urls)) {
    return -1;
  }
  printf("b\n");
  self->protocols = malloc(sizeof(struct libwebsocket_protocols)*2);
  if(!self->protocols) {
    return -1;
  } else {
    self->protocols[0].name                  = "http-only";
    self->protocols[0].callback              = WebSocket_http_callback;
    self->protocols[0].per_session_data_size = 0;

    self->protocols[1].name                  = NULL;
    self->protocols[1].callback              = NULL;
    self->protocols[1].per_session_data_size = 0;
  }
  self->numprotocols = 1;
  self->running                       = false;

  self->dispatch                      = PyDict_New();
  self->connections                   = PyDict_New();
  self->urls                          = urls;
  if(!self->dispatch) {
    return -1;
  }

  self->info.port                     = port;
  self->info.iface                    = interface;
  self->info.protocols                = self->protocols;
  self->info.extensions               = NULL;
  self->info.ssl_cert_filepath        = NULL;  //cert_path;
  self->info.ssl_private_key_filepath = NULL;  //key_path;
  self->info.options = 0; 
  self->info.user = (void *)self;
  printf("c\n");
  return 0;
}

static PyObject *WebSocket_register_protocol(WebSocketObject *self, PyObject *args)
{
printf("x %d\n",self->numprotocols);
PyObject *func;
PyObject *name;
  if ( PyArg_ParseTuple(args, "OO", &name, &func)) {

    size_t nextsize = sizeof(struct libwebsocket_protocols)*(self->numprotocols+2);
    self->protocols = realloc(self->protocols, nextsize);
    
    if(!self->protocols) {
      Py_RETURN_NONE;
    }

    self->info.protocols = self->protocols;
    
    PyDict_SetItem(self->dispatch, name, func);
    self->protocols[self->numprotocols+1] = self->protocols[self->numprotocols];
    
    Py_ssize_t namelen = PyString_Size(name);
    char *namestr = malloc(namelen+1);
    if(!namestr){
      Py_RETURN_NONE;
    }
    printf("pystring = %s len = %d\n",PyString_AsString(name),PyString_Size(name));
    strncpy(namestr,PyString_AsString(name), namelen+1);
    
    self->protocols[self->numprotocols].name                  = namestr;
    self->protocols[self->numprotocols].callback              = WebSocket_dispatch;
    self->protocols[self->numprotocols].per_session_data_size = 0;
    self->numprotocols++;
    printf("new protocol --> %s\n", namestr);
  }
  // TODO: Raise ValueError here  
  Py_RETURN_NONE;
}
static void WebSocket_dealloc(WebSocketObject *self)
{ 
  //libwebsocket_context_destroy(self->context);
  for (int i=1; i<self->numprotocols; i++) {
    free((void *)self->protocols[i].name);
  }
  free(self->protocols);
  Py_DECREF(self->dispatch);
  self->ob_type->tp_free((PyObject*)self);
}

static PyMethodDef WebSocket_methods[] = {
  {"run", (PyCFunction)WebSocket_run, METH_VARARGS,
   "Run websocket server (for n milliseconds)"
  },
  {"register", (PyCFunction)WebSocket_register_protocol, METH_VARARGS,
   "bind a protocol name to a callback function"
  },
  {"listen", (PyCFunction)WebSocket_listen, METH_VARARGS,
   "tell lib websockets to start listening"
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
  0,                   /* tp_traverse */
  0,                   /* tp_clear */
  0,                   /* tp_richcompare */
  0,                   /* tp_weaklistoffset */
  0,                   /* tp_iter */
  0,                   /* tp_iternext */
  WebSocket_methods,          /* tp_methods */
  0,                         /* tp_members */
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
