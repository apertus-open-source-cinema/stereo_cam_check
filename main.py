#!/usr/bin/python

#       Program to check inputs from a stereo camera
#       pair (Elphels) before actually shooting
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING

#       Application structure is very simple:
#       1. Ask user for two video streams to display
#       2. Show them. User can change the view a bit,
#       but that's all. Once they're happy, they quit.


# One day we'll be running under Python 3
from __future__ import division, print_function

import sys, os

# This chdirs into the program home so we can
# load plugins, shaders, etc
progDir = os.path.dirname(__file__)
if progDir:
    os.chdir(progDir)

import wx

import app, chooser, renderer
from app import _


class CameraFrame(wx.Frame):
    # Main window for stereo camera checker app
    # Startup config is mostly chooser.py, display is renderer.py
    
    def __init__(self, parent, id, title, pos, size):
        prefSize = eval(app.config.Read("windowSize", "None"))
        if prefSize is None:
            prefSize = size
        wx.Frame.__init__(self, parent, id, title=title,
                        pos=pos, size=prefSize)
        self.canvas = renderer.StereoFrame(self)
        self.dlg = None
        self.makeMenuBar()
        self.CreateStatusBar()
        self.Bind(wx.EVT_CLOSE, self.OnClose, self)
        
    def makeMenuBar (self):
        # This is a very simple app, so there's only one menu
        fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_ABOUT, _("About..."))
        # Renderer gets to add some view controls
        self.canvas.addMenuItems(fileMenu)
        fileMenu.AppendSeparator()
        # Boilerplate. Fairly sure this will never run
        # on anything but Linux, but I always do this
        if wx.Platform == "__WXMAC__":
            exitStr = _("Quit\tctrl+q")
        else:
            exitStr = _("Exit\tctrl+w")
        fileMenu.Append(wx.ID_EXIT, exitStr)
        #
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "StereoCamCheck")
        self.SetMenuBar(menuBar)
        #
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=wx.ID_EXIT)
        
    def setVideoStreams(self, left, right, pipeline):
        # Renderer does most of the work
        if not left:
            # Swap with right
            left  = right
            right = ""
        self.SetStatusText(str(left) + " : " + str(right))
        if pipeline == "":
            pipeline = None
        self.canvas.setVideoStreams(left, right, pipeline)
    
    def OnAbout(self, event):
        wx.MessageBox(
            "Stereo camera check\n" +
            _("Version 1.3\n") + 
            _("Programming: Hugh Fisher\n") +
            _("CECS, ANU, 2011\n") +
            _("Stereo video experts: Winnie Yang and Nathan Clark\n") +
            "\n" +
            _("Thanks to the wxWidgets and wxPython teams,") +
            _(" Mike Fletcher for PyOpenGL,") +
            _(" Morgan McGuire for GPU Bayer demosaic code"),
            _("About StereoCamCheck"), wx.OK | wx.ICON_INFORMATION, self)
    
    def OnClose(self, event):
        app.config.Write("windowSize", repr(self.GetSizeTuple()))
        self.canvas.stopVideo()
        if self.dlg:
            self.dlg.Close()
        self.Destroy()
    
    def OnQuit(self, event):
        self.Close()

    
class StereoCheckApp(wx.App):
    
    def OnInit(self):
        self.createFrame()
        self.chooseInput()
        return True
    
    def createFrame(self):
        self.frame = CameraFrame(parent=None, id=wx.ID_ANY,
                    title=_("Stereo Camera Check"),
                    pos=wx.DefaultPosition,
                    size=(800, 600 + 52))
        self.frame.Show()
        self.SetTopWindow(self.frame)
    
    def chooseInput(self):
        dlg = chooser.SourceDialog()
        result = dlg.ShowModal()
        if result != wx.ID_OK:
            # If cancelled, quit straight away
            dlg.Destroy()
            raise SystemExit
        src = dlg.getVideoSources()
        # Need at least one input
        if not (src[0] or src[1]):
            dlg.Destroy()
            raise SystemExit
        self.frame.setVideoStreams(src[0], src[1], dlg.getGSTPipeline())
        # Remember config for next time
        dlg.saveChoices()
        dlg.Destroy()


##      Main


if __name__ == "__main__":
    TheApp = StereoCheckApp()
    TheApp.MainLoop()

