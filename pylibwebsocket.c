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
    WebSocketObject *self=user;
    // reason for callback
    switch (reason) {

        case LWS_CALLBACK_ESTABLISHED:
            printf("connection established\n");
            break;

        case LWS_CALLBACK_RECEIVE: {
            cur_protocol = libwebsockets_get_protocol (wsi);
            PyObject *callback = PyDict_GetItemString(self->dispatch,cur_protocol->name);
            if(callback) {
              PyObject_CallFunction(callback, "ss", cur_protocol, in);
            }            
            printf("received data: %s\n", (char *) in);
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
    int return_value = 0; 
    switch (reason) {
        // http://git.warmcat.com/cgi-bin/cgit/libwebsockets/tree/lib/libwebsockets.h#n260
        case LWS_CALLBACK_CLIENT_WRITEABLE:
            printf("connection established\n");
            
        // http://git.warmcat.com/cgi-bin/cgit/libwebsockets/tree/lib/libwebsockets.h#n281
        case LWS_CALLBACK_HTTP: {
            char *requested_uri = (char *) in;
            printf("requested URI: %s\n", requested_uri);
            
            if (strcmp(requested_uri, "/") == 0) {
                void *universal_response = "Hello, World!";
                // http://git.warmcat.com/cgi-bin/cgit/libwebsockets/tree/lib/libwebsockets.h#n597
                libwebsocket_write(wsi, universal_response,
                                   strlen(universal_response), LWS_WRITE_HTTP);
                break;
 
            } else {
                // try to get current working directory
                char cwd[1024];
                char *resource_path;
                
                if (getcwd(cwd, sizeof(cwd)) != NULL) {
                    // allocate enough memory for the resource path
                    resource_path = malloc(strlen(cwd) + strlen(requested_uri));
                    
                    // join current working direcotry to the resource path
                    sprintf(resource_path, "%s%s", cwd, requested_uri);
                    printf("resource path: %s\n", resource_path);
                    
                    char *extension = strrchr(resource_path, '.');
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
                    libwebsockets_serve_http_file(context, wsi, resource_path, mime, NULL);
                    free(resource_path); 
                }
            }
            
            // close connection
            return_value = -1;
            break;
        }
        default:
            printf("unhandled callback\n");
            break;
    }
    
    return return_value;
}
 




static int WebSocket_init(WebSocketObject *self, 
                          PyObject *args)
{
  int   port;
  char *interface;
  char *cert_path;
  char *key_path;

  if (! PyArg_ParseTuple(args, "siss", 
                         &interface, &port,
                         &cert_path, &key_path)) {
    return -1;
  }
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

  self->running                       = false;

  self->dispatch                      = PyDict_New();
  if(!self->dispatch) {
    return -1;
  }

  self->info.port                     = port;
  self->info.iface                    = interface;
  self->info.protocols                = self->protocols;
  self->info.extensions               = NULL;
  self->info.ssl_cert_filepath        = cert_path;
  self->info.ssl_private_key_filepath = key_path;
  self->info.options = 0; 
  self->info.user = (void *)self;
  return 0;
}

static PyObject *WebSocket_register_protocol(WebSocketObject *self, PyObject *args)
{
PyObject *func;
PyObject *name;
  if ( PyArg_ParseTuple(args, "OO", &name, &func)) {
    realloc(self->protocols,sizeof(struct libwebsocket_protocols)*self->numprotocols+2);
    if(!self->protocols) {
      Py_RETURN_NONE;
    }

    PyDict_SetItem(self->dispatch, name, func);

    memcpy(&self->protocols[self->numprotocols],
           &self->protocols[self->numprotocols+1],
           sizeof(struct libwebsocket_protocols));
    Py_ssize_t namelen = PyString_Size(name);
    char *namestr = malloc(namelen+1);
    if(!namestr){
      Py_RETURN_NONE;
    }
    strncpy(namestr,PyString_AsString(name), namelen);
    
    self->protocols[self->numprotocols].name                  = namestr;
    self->protocols[self->numprotocols].callback              = WebSocket_dispatch;
    self->protocols[self->numprotocols].per_session_data_size = 0;
    self->numprotocols++;
  }
  // TODO: Raise ValueError here  
  Py_RETURN_NONE;
}
static void WebSocket_dealloc(WebSocketObject *self)
{ 
  //libwebsocket_context_destroy(self->context);
  for (int i=0; i<self->numprotocols; i++) {
    free((void *)self->protocols[i].name);
  }
  free(self->protocols);
  self->ob_type->tp_free((PyObject*)self);
}

static PyMethodDef WebSocket_methods[] = {
  {"run", (PyCFunction)WebSocket_run, METH_VARARGS,
   "Run websocket server (for n milliseconds)"
  },
  {"run", (PyCFunction)WebSocket_register_protocol, METH_VARARGS,
   "Run websocket server (for n milliseconds)"
  },
  {"run", (PyCFunction)WebSocket_dispatch, METH_VARARGS,
   "Run websocket server (for n milliseconds)"
  },
  {"run", (PyCFunction)WebSocket_listen, METH_VARARGS,
   "Run websocket server (for n milliseconds)"
  },
  {NULL}  /* Sentinel */
};


static PyTypeObject WebSocketType = {
  PyObject_HEAD_INIT(NULL)
  0,                         /*ob_size*/
  "libwebsocket.WebSocket",  /*tp_name*/
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
  "LibWebSocket is a Python C extension library that implements a data structure\n"
  "useful for doing spatial indexing.  If you have thousands of objects, and\n"
  "need to quickly find out what objects are close to each other, this class\n"
  "is very useful.\n",
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
initwebsocket(void) 
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