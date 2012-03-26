

#       3D display code for stereo camera preview
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING

#       The renderer displays the two video sources.
#       Current options are side by side, overlaid at
#       50% alpha each, or anaglyph (red-blue) stereo
#       Real quad buffered stereo might be nice, but
#       this app was designed for use in the field on
#       a laptop.

from __future__ import division, print_function

import sys, math

import wx
from wx.glcanvas import *

import pygst, gst

import OpenGL
from OpenGL import GL
from OpenGL.GL import *

from canvas3d import Canvas3D
import app
from app import _
import gpu, gstvideo, videotexture
from videotexture import *

# Because these integers get stored in app prefs,
# never add new ids before them.
MYID_SPLIT      = wx.ID_HIGHEST + 1
MYID_BLENDED    = MYID_SPLIT + 1
MYID_ANAGLYPH   = MYID_BLENDED + 1
MYID_FULLSCREEN = MYID_ANAGLYPH + 1

    
class StereoFrame(Canvas3D):
    """Display frame stereo image pair"""
    
    def __init__(self, parent, size = None, attribs = None, id = wx.ID_ANY):
        Canvas3D.__init__(self, parent, size, attribs, id)
        self.window  = parent
        self.prevKey = None
        # Streams, to be supplied
        self.left    = None
        self.right   = None
        self.pipeline= None
        # Single, side by side or overlay view
        self.mono    = True # Automatic if only one stream, no preference
        self.overlay = eval(app.config.Read("overlay", "0"))
        self.bkColor = (0.0, 0.0, 0.0)  # Background color
        # Internal layout
        self.BORDER  = 0.1
    
    def stopVideo(self):
        """Shut down GStreamer, save prefs"""
        if self.left:
            self.left.stop()
        if self.right:
            self.right.stop()
        app.config.Write("overlay", repr(self.overlay))
    
    def addMenuItems(self, menu):
        """Our view controls"""
        self.menu = menu
        menu.Append(MYID_FULLSCREEN, _("Full screen\tctrl+f"))
        menu.AppendSeparator()
        menu.AppendCheckItem(MYID_BLENDED, _("Blended view\tctrl+b"))
        menu.AppendCheckItem(MYID_SPLIT, _("Side by side\tctrl+s"))
        menu.AppendCheckItem(MYID_ANAGLYPH, _("Anaglyph view\tctrl+a"))
        self.window.Bind(wx.EVT_MENU, self.OnFullScreen, id=MYID_FULLSCREEN)
        self.window.Bind(wx.EVT_MENU, self.OnSplit, id=MYID_SPLIT)
        self.window.Bind(wx.EVT_MENU, self.OnMerge, id=MYID_BLENDED)
        self.window.Bind(wx.EVT_MENU, self.OnAnaglyph, id=MYID_ANAGLYPH)
        # Immediate update, wx always checks first item
        self.OnUpdateMenu(None)
    
    def setVideoStreams(self, left, right, pipeline):
        """Create video streams from chooser dialog values"""
        # If only one stream (mono), make it the left
        self.left = VideoTexture(left, pipeline)
        if not right:
            self.mono = True
        else:
            self.mono = False
            self.right = VideoTexture(right, pipeline)
        self.positionStreams()
        # The video streams update the GL textures automatically,
        # but don't force window updates. We'll draw at normal
        # speed rather than try to synch to the video frame rate.
        self.animate()
        self.OnUpdateMenu(None)
     
    def OnFullScreen(self, event):
        """Change to fullscreen mode"""
        self.window.ShowFullScreen(not self.window.IsFullScreen(), style=wx.FULLSCREEN_ALL)
    
    def OnSplit(self, event):
        """Switch to split view, with animation"""
        self.overlay = 0
        self.positionStreams()
        self.OnUpdateMenu(None)
    
    def OnMerge(self, event):
        """Switch to blended overlay view"""
        self.overlay = MYID_BLENDED
        self.positionStreams()
        self.OnUpdateMenu(None)
    
    def OnAnaglyph(self, event):
        """Switch to red-blue overlay view"""
        self.overlay = MYID_ANAGLYPH
        self.positionStreams()
        self.OnUpdateMenu(None)
    
    def OnUpdateMenu(self, event):
        """Auto update of menu status"""
        if self.mono:
            self.menu.Enable(MYID_SPLIT, False)
            self.menu.Enable(MYID_BLENDED, False)
            self.menu.Enable(MYID_ANAGLYPH, False)
        else:
            self.menu.Enable(MYID_SPLIT, True)
            self.menu.Enable(MYID_BLENDED, True)
            self.menu.Enable(MYID_ANAGLYPH, True)
            self.menu.Check(MYID_SPLIT, not self.overlay)
            self.menu.Check(MYID_BLENDED, self.overlay == MYID_BLENDED)
            self.menu.Check(MYID_ANAGLYPH, self.overlay == MYID_ANAGLYPH)
    
    def key(self, event):
        """Quit on ESC, others ignored"""
        ch = event.GetKeyCode()
        if ch == wx.WXK_ESCAPE:
            if self.prevKey == ch:
                self.window.Close()
        else:
            event.Skip()
        self.prevKey = ch
    
    def OnSize(self, event):
        Canvas3D.OnSize(self, event)
        self.positionStreams(True)
    
    def initGL(self):
        Canvas3D.initGL(self)
        glClearColor(self.bkColor[0], self.bkColor[1], self.bkColor[2], 0)
        glDisable(GL_DEPTH_TEST)
        glEnableClientState(GL_VERTEX_ARRAY)
        self.initShaders()
    
    def initShaders(self):
        gpu.init()
        # Flat shader used for overlays
        stdVert = gpu.loadShaderFile(GL_VERTEX_SHADER, "std_vert.glsl",
                ["#version 120"])
        flatFrag = gpu.loadShaderFile(GL_FRAGMENT_SHADER, "flat_frag.glsl")
        self.flatShader = gpu.newProgram(stdVert, flatFrag)
        # The video shaders vary depending on the source
        # format (Bayer or non) and output (RGB or red-blue)
        # Could recompile shaders on the fly as the output
        # changes, but easier to generate all variations here
        ## RGB shader just uses image as texture
        rgbFrag = gpu.loadShaderFile(
                GL_FRAGMENT_SHADER, "video_frag.glsl",
                ["#version 120"])
        self.rgbVideo = gpu.newProgram(stdVert, rgbFrag)
        h = gpu.getUniform(self.rgbVideo, "image")
        glUniform1i(h, 0)   # Always GL_TEXTURE0
        # RGB anaglyph shader
        rgbAnaglyphFrag = gpu.loadShaderFile(
                GL_FRAGMENT_SHADER, "video_frag.glsl",
                ["#version 120", "#define ANAGLYPH"])
        self.rgbAnaglyphVideo = gpu.newProgram(stdVert, rgbAnaglyphFrag)
        h = gpu.getUniform(self.rgbAnaglyphVideo, "image")
        glUniform1i(h, 0)
        ## Bayer demosaic versions
        bayerVert = gpu.loadShaderFile(GL_VERTEX_SHADER, "std_vert.glsl",
                ["#version 120", "#define DEBAYER"])
        bayerFrag = gpu.loadShaderFile(
                GL_FRAGMENT_SHADER, "video_frag.glsl",
                ["#version 120", "#define DEBAYER"])
        self.bayerVideo = gpu.newProgram(bayerVert, bayerFrag)
        h = gpu.getUniform(self.bayerVideo, "image")
        glUniform1i(h, 0)
        bayerAnaglyphFrag = gpu.loadShaderFile(
                GL_FRAGMENT_SHADER, "video_frag.glsl",
                ["#version 120", "#define DEBAYER", "#define ANAGLYPH"])
        self.bayerAnaglyphVideo = gpu.newProgram(bayerVert, bayerAnaglyphFrag)
        h = gpu.getUniform(self.bayerAnaglyphVideo, "image")
        glUniform1i(h, 0)
    
    def positionStreams(self, force=False):
        """Position streams within window according to display option"""
        if self.overlay == 0:
            # Side by side mode
            maxFrac = 0.5
            if self.left:
                self.left.place(-1.0, -0.5, self, force, maxFrac)
            if self.right:
                self.right.place(0.0, -0.5, self, force, maxFrac)
        else:
            # Overlay blended/anaglyph
            maxFrac = 1.0
            if self.left:
                self.left.place(-0.5, -0.5, self, force, maxFrac)
            if self.right:
                self.right.place(-0.5, -0.5, self, force, maxFrac)
        
    def setProjection(self):
        """As of version 1.3 switched to integer pixel coords
           for more accurate video display on large monitors"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
    
    def setViewpoint(self):
        glLoadIdentity()
    
    def drawSingleStream(self):
        """Draw a single non-stereo stream"""
        if self.left.bayer:
            gpu.useProgram(self.bayerVideo)
        else:
            gpu.useProgram(self.rgbVideo)
        glDisable(GL_BLEND)
        self.left.draw()
    
    def drawSideBySide(self):
        """Side by side view of stereo stream pair"""
        if self.left.bayer or self.right.bayer:
            gpu.useProgram(self.bayerVideo)
        else:
            gpu.useProgram(self.rgbVideo)
        glDisable(GL_BLEND)
        self.left.draw()
        self.right.draw()
        # Separator
        gpu.useProgram(self.flatShader)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0,
                ((self.width/2, 0) ,(self.width/2, self.height)))
        glColorPointer(3, GL_FLOAT, 0,
                (self.bkColor, self.bkColor))
        glDrawArrays(GL_LINES, 0, 2)
        glDisableClientState(GL_COLOR_ARRAY)
    
    def drawBlendedStreams(self):
        """Stream pair each at 50% opacity"""
        if self.left.bayer or self.right.bayer:
            gpu.useProgram(self.bayerVideo)
        else:
            gpu.useProgram(self.rgbVideo)
        glEnable(GL_BLEND)
        glBlendColor(1.0, 1.0, 1.0, 1.0)
        glBlendFunc(GL_ONE, GL_ZERO)
        self.left.draw()
        glBlendColor(1.0, 1.0, 1.0, 0.5)
        glBlendFunc(GL_CONSTANT_ALPHA, GL_ONE_MINUS_CONSTANT_ALPHA)
        self.right.draw()
    
    def drawRedBlueStreams(self):
        """Red-blue stereo view of grayscale"""
        if self.left.bayer or self.right.bayer:
            gpu.useProgram(self.bayerAnaglyphVideo)
        else:
            gpu.useProgram(self.rgbAnaglyphVideo)
        glDisable(GL_BLEND)
        glColorMask(GL_TRUE, GL_FALSE, GL_FALSE, GL_FALSE)
        self.left.draw()
        glColorMask(GL_FALSE, GL_TRUE, GL_TRUE, GL_FALSE)
        self.right.draw()
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
    
    def drawWorld(self):
        if self.left is None and self.right is None:
            return
        # There's a bunch of different ways to draw the stream(s)
        if self.mono:
            self.drawSingleStream()
        elif not self.overlay:
            self.drawSideBySide()
        elif self.overlay == MYID_BLENDED:
            self.drawBlendedStreams()
        elif self.overlay == MYID_ANAGLYPH:
            self.drawRedBlueStreams()
    
    
    
