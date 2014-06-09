from distutils.core import setup, Extension
setup(name="pylws", version="1.0",
      ext_modules=[Extension("pylws", 
                             ["pylibwebsocket.c"],
                             libraries=['websockets'],
                             library_dirs=['/usr/local/lib'],
                             extra_compile_args=['-std=c99']
                             )])
