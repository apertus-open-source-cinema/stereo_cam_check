

#       OpenGL frame class for wx applications.
#       Written by Hugh Fisher, CECS ANU, 2010

# Don't edit this unless there are actual bugs: it's
# supposed to be shared code across applications.

from __future__ import division

import wx
from wx.glcanvas import *

import OpenGL
from OpenGL import GLU
from OpenGL import GL
from OpenGL.GL import *
from OpenGL.GLU import *

class Canvas3D(GLCanvas):
    """Superclass for 3D frame"""

    def __init__(self, parent, size = None, attribs = None, id = wx.ID_ANY):
        if not attribs:
            attribs = [WX_GL_RGBA, WX_GL_DOUBLEBUFFER, WX_GL_DEPTH_SIZE, 24]
        GLCanvas.__init__(self, parent, id, attribList=attribs, size=size)
        # We handle erase ourself, stops flickering on MS Windows
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.init   = False
        self.width  = 0
        self.height = 0
        self.near   = 1.0
        self.far    = 100.0
        self.FOV    = 60
        # Display event handlers
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        # Simple keyboard handler
        self.Bind(wx.EVT_CHAR, self.key)
        # Animation off by default
        self.timer = None

    def OnPaint(self, event):
        self.DC = wx.PaintDC(self)
        self.SetCurrent()
        if not self.init:
            self.initGL()
        self.clear()
        self.setProjection()
        self.setViewpoint()
        self.drawWorld()
        self.SwapBuffers()
        # This forces the DC to be destroyed, which is
        # necessary on MS Windows to invoke a destructor
        # method that clears the Paint event. Sigh.
        self.DC = None

    def OnSize(self, event):
        # Note these are ints, not floats, for glViewport
        self.width, self.height = self.GetSizeTuple()

    def animate(self, millisecsPerUpdate = 0):
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update)
        if millisecsPerUpdate == 0:
            # 60 frames/sec is a useful default
            millisecsPerUpdate = 1000.0 / 60.0
        self.timer.Start(millisecsPerUpdate)

    # Override these do do useful stuff

    def initGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glDisable(GL_DITHER)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_DEPTH_TEST)
        self.init = True
    #
    def clear(self):
        glViewport(0, 0, self.width, self.height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def setProjection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.FOV, float(self.width) / float(self.height), self.near, self.far)
        glMatrixMode(GL_MODELVIEW)

    def setViewpoint(self):
        glLoadIdentity()
        gluLookAt(0.0, 1.0, -5.0,
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)

    def drawWorld(self):
        pass

    def key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.GetParent().Close()

    def update(self, event):
        self.Refresh()




