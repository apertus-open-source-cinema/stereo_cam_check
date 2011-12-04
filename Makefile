
# Hugh Fisher, CECS, 2011
# Makefile for building GLTextureSink plugin as part of
# Python program. You could instead build it as a regular
# GStreamer plugin and install it with all the others.

PLUG = gstgltexturesink

CC = gcc
CFLAGS += -fPIC -Wall

# Must build with glib, gst, and gst base classes
CFLAGS += `pkg-config --cflags glib-2.0`
LIBS += `pkg-config --libs glib-2.0`
CFLAGS += `pkg-config --cflags gstreamer-0.10`
LIBS += `pkg-config --libs gstreamer-0.10` -lgstbase-0.10 -lgstvideo-0.10
# Plus OpenGL
LIBS += -lGL

# I think the .so version is the GStreamer version.
CFLAGS += -DVERSION=\"0.10\"

# This builds as a Python module that registers itself
# when imported
CFLAGS += -DEMBEDDED_PYTHON -I/usr/include/python2.6
LIBS += -lpython2.6

#For a standard plugin, change -o name to lib$(PLUG).so
default: $(PLUG).o
	$(CC) -shared -Wl,--no-undefined	\
	-o $(PLUG).so				\
	$(PLUG).o				\
	-Wl,-soname,$(PLUG).so.$(VERSION)	\
	$(LIBS)

clean:
	/bin/rm -f *.o *.so

$(PLUG).o: $(PLUG).h $(PLUG).c

# Utility

dist:
	/bin/rm -f *.o *.pyc *.so
	(cd .. ; tar -cvf stereocamcheck.tar --exclude='.svn' StereoCamCheck)

