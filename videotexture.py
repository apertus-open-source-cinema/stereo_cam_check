

#       Video texture for stereo camera preview
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING


from __future__ import division, print_function

import sys, math

import wx
from wx.glcanvas import *

import pygst, gst

import OpenGL
from OpenGL import GL
from OpenGL.GL import *

import app, gpu, gstvideo
from app import _


def lerp(x, y, a):
    """Animation utility, interpolate between two values"""
    return (x * (1.0 - a)) + (y * a)

def fit(w, h, maxW, maxH):
    """Return scale factor to fit rectangle within limit"""
    for s in (1, 2/3, 1/2, 1/3, 1/4):
        # According to users, OK to chop a bit off top and bottom
        if w * s <= maxW and h * s <= maxH * 1.05:
            return s
    # If we get here, who knows?
    return 0.1

class Vec2f(object):
    """Convenience class for storing 2D values.
       wx.Point is integer coords, need float"""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
    # Use as size
    @property
    def w(self): return self.x
    @property
    def h(self): return self.y


class Rect(object):
    """Convenience class for storing rectangles"""
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)
    
    def copy(self):
        return Rect(self.x, self.y, self.w, self.h)
    
    @staticmethod
    def step(r1, r2, a):
        """Return rect in between r1 and r2, 0 <= a <= 1"""
        if a <= 0.0:
            return r1.copy()
        elif a >= 1.0:
            return r2.copy()
        else:
            return Rect(lerp(r1.x, r2.x, a), lerp(r1.y, r2.y, a),
                        lerp(r1.w, r2.w, a), lerp(r1.h, r2.h, a))

class VideoTexture(object):
    """Display single GStreamer video source within OpenGL
       view. Drawn from bottom left, animated move to position"""
    instCounter = 0
    
    def __init__(self, source, gstPipeline):
        # Can't really do anything until first frame arrives
        self.live = False
        # This allows app to show/hide
        self.visible = True
        self.initTexture()
        self.initLayout()
        self.connectSource(source, gstPipeline)
    
    def newSinkName(self):
        """Generate unique name for Gst object"""
        VideoTexture.instCounter += 1
        return "glsink" + str(VideoTexture.instCounter)
    
    def initLayout(self):
        """Set up position and size for display"""
        # Set by app to position, scale video
        self.fx     = 0
        self.fy     = 0
        self.maxArea= 1.0
        # Actual dimensions depend on video data. Assume
        # 4:3 for now so calculations don't break
        self.dest   = Rect(0, 0, 4/3, 1)
        self.start  = self.dest.copy()
        self.box    = self.dest.copy()
        self.animStep = 0.0
        self.canvas = None
        self.scale  = 1.0
        # Tex coords, video dimensions must wait until first use
        self.tex = Vec2f(0, 0)
        self.vid = Vec2f(0, 0)
        self.firstFrame = False
    
    def initTexture(self):
        """Create OpenGL texture and GstGLTextureSink"""
        self.texID = glGenTextures(1)
        # Now create the GstGLTextureSink
        self.sink = gst.element_factory_make("gltexturesink", self.newSinkName())
        self.sink.set_property("texture", self.texID)
        # State we need to track
        self.bayer = False
        self.prog  = None
    
    def connectSource(self, source, pipeline):
        """Try and open video source, attach texture sink"""
        # First, create pipeline. (Which presumably is open-ended)
        if pipeline is None:
            pipeline = gstvideo.defaultPipeline(source)
        # Apply any gltexturesink params and create pipeline
        pipeline = gstvideo.configSink(self.sink, pipeline)
        self.stream = gstvideo.createPipeline(source, pipeline)
        # Get last element
        if isinstance(self.stream, gst.Bin):
            chain = [e for e in self.stream.sorted()]
            src = chain[0]
        else:
            src = self.stream
        # And try and attach to end of it
        self.stream.add(self.sink)
        try:
            src.link(self.sink)
        except:
            wx.MessageBox(_("Unable to link GLTextureSink to pipeline\n") +
                        _("Source:") + str(source) + "\n" +
                        _("Pipeline:") + str(pipeline) + "\n",
                        _("Error creating GST pipeline"),
                        wx.OK | wx.ICON_ERROR, None)
            raise RuntimeError("Unable to link GLTextureSink to pipeline")
        # We're good
        self.stream.set_state(gst.STATE_PLAYING)
    
    def stop(self):
        self.stream.set_state(gst.STATE_NULL)
    
    def setVisible(self, state):
        self.visible = state
    
    def checkLive(self):
        if self.live:
            return True
        # Try to get dimensions from GLTextureSink
        self.vid = Vec2f(self.sink.get_property("width"),
                         self.sink.get_property("height"))
        if self.vid.w > 0 and self.vid.h > 0:
            self.tex = Vec2f(1.0, 1.0)
            self.bayer = self.sink.get_property("is_bayer")
            self.resize()
            self.setCoords()
            self.live = True
        return self.live
    
    def place(self, fx, fy, canvas, force=False, maxArea=1.0):
        """Place texture relative to midpoint of canvas.
           fx, fy are fractions of width/height, can be
           negative. force True to turn off animated move.
           maxArea restricts display width to fraction of
           total canvas"""
        # Remember values
        self.fx = fx
        self.fy = fy
        self.maxArea = maxArea
        if self.canvas is None:
            self.canvas = canvas
        # Apply now or later?
        if self.live:
            self.resize(force)
            self.setCoords(force)
    
    def resize(self, force=True):
        """Resize display box to match texture, either
           animating to new size or force straight away"""
        self.scale = fit(self.vid.w, self.vid.h,
            self.canvas.width * self.maxArea, self.canvas.height)
        # Use of canvas height for dest.w is not a mistake
        self.dest.w = self.vid.w * self.scale / self.canvas.height
        self.dest.h = self.vid.h * self.scale / self.canvas.height
        if force:
            self.start.w = self.dest.w
            self.start.h = self.dest.h
            self.box.w   = self.dest.w
            self.box.h   = self.dest.h
    
    def setCoords(self, force=True):
        """Set location (not size) on live texture"""
        self.dest.x = self.fx * self.dest.w
        self.dest.y = self.fy * self.dest.h
        if force:
            self.box = self.dest.copy()
            self.animStep = 1.0
        else:
            self.start = self.box.copy()
            self.animStep = 0.0
    
    def slide(self):
        """Animated slide into new position within canvas"""
        if self.animStep >= 1.0:
            return
        self.animStep = min(self.animStep + 0.2, 1.0)
        self.box = Rect.step(self.start, self.dest, self.animStep)
    
    def configShader(self):
        """Set uniforms in current GPU program"""
        if self.bayer:
            shader = gpu.getProgram()
            h = gpu.getUniform(shader, "sourceSize")
            glUniform4f(h, self.vid.w, self.vid.h, 1.0/self.vid.w, 1.0/self.vid.h)
            h = gpu.getUniform(shader, "firstRed")
            # This is the RGGB ordering that works with Elphel
            glUniform2f(h, 1, 0)
    
    def draw(self):
        # First actual frame has arrived?
        if not self.checkLive():
            return
        # App allows display?
        if not self.visible:
            return
        # App has changed shaders?
        if gpu.getProgram() != self.prog:
            self.configShader()
            self.prog = gpu.getProgram()
        # Animated slide to new position?
        self.slide()
        # Just rect with texture coords
        glBindTexture(GL_TEXTURE_2D, self.texID)
        glEnable(GL_TEXTURE_2D)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        verts = (
            self.box.x, self.box.y + self.box.h,    # Upper left
            self.box.x, self.box.y,                 # Lower left
            self.box.x + self.box.w, self.box.y + self.box.h,   # Upper right
            self.box.x + self.box.w, self.box.y,                # Lower right
        )
        # GStreamer has image origin at top left
        texCoords = (
            0, 0,
            0, self.tex.h,
            self.tex.w, 0,
            self.tex.w, self.tex.h,
        )
        glVertexPointer(2, GL_FLOAT, 0, verts)
        glTexCoordPointer(2, GL_FLOAT, 0, texCoords)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)

