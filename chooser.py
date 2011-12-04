
#       Input stream chooser for stereo camera preview
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING

#       The user can/must choose:
#       Two video sources to display. These can be pre-recorded
#       files or RTSP streams.
#       Optional: GStreamer pipeline to be applied to each
#       source before display. This is necessary for any source
#       that isn't type x-raw-rgb

#       Since this app is probably going to be run frequently,
#       it tries to remember the configuration used last time.
#       On Linux, these values are stored in $HOME/.StereoCamCheck

from __future__ import division, print_function

import wx

import app, gstvideo
from app import _

class SourceDialog(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, wx.ID_ANY,
                _("Source Chooser"),
                pos=wx.DefaultPosition, size=wx.DefaultSize)
        # From top to bottom, two video sources; GStreamer pipeline; button
        vert = wx.BoxSizer(wx.VERTICAL)
        #
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.left, w = self.makeSource(_("Left eye"), "Left eye", self.setLeftToFile)
        row.Add(w, 1, wx.ALIGN_LEFT | wx.EXPAND)
        self.right, w = self.makeSource(_("Right eye"), "Right eye", self.setRightToFile)
        row.Add(w, 1, wx.ALIGN_LEFT | wx.EXPAND)
        vert.Add(row, 0, wx.ALIGN_LEFT | wx.EXPAND | wx.ALL, 32)
        #
        w = wx.StaticText(self, wx.ID_ANY, _("GStreamer pipeline"))
        vert.Add(w, 0, wx.ALIGN_CENTRE)
        previous = self.getStoredList("pipeline")
        currPipe = ""
        if len(previous) == 0:
            previous = gstvideo.defaultPipes()
            self.storeList("pipeline", previous)
        else:
            idx = self.getStoredInt("pipeline")
            if isinstance(idx, int):
                currPipe = previous[idx]
        self.pipeline = wx.ComboBox(self, wx.ID_ANY, choices=previous)
        self.pipeline.SetValue(currPipe)
        vert.Add(self.pipeline, 0, wx.ALIGN_LEFT | wx.EXPAND | wx.LEFT | wx.RIGHT, 32)
        #
        self.ok = wx.Button(self, wx.ID_OK, "OK")
        self.ok.SetDefault()
        vert.Add(self.ok, 0, wx.ALIGN_CENTRE | wx.ALL, 32)
        #
        self.SetSizer(vert)
        self.Fit()
    
    def getVideoSources(self):
        """Return current source values from dialog box"""
        return (self.left.GetValue(), self.right.GetValue())
    
    def getGSTPipeline(self):
        """Return pipeline from dialog box"""
        return self.pipeline.GetValue()
    
    def saveChoices(self):
        """App must invoke this, it's not automatic"""
        leftURI, rightURI = self.getVideoSources()
        self.storeListEntry("Left eye", leftURI)
        self.storeListEntry("Right eye", rightURI)
        pipe = self.getGSTPipeline()
        if len(pipe) > 0:
            self.storeListEntry("pipeline", pipe, len(gstvideo.defaultPipes()))
    
    def makeSource(self, name, key, setter):
        """Create widgets to select source. Return text entry, top level"""
        box = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, wx.ID_ANY, name)
        box.Add(label, 0, wx.ALIGN_LEFT)
        previous = self.getStoredList(key)
        entry = wx.ComboBox(self, wx.ID_ANY, choices=previous)
        idx = self.getStoredInt(key)
        if isinstance(idx, int): # Don't use if idx: zero is false!
            entry.SetSelection(idx)
        box.Add(entry, 0, wx.ALIGN_LEFT | wx.EXPAND)
        id = wx.NewId()
        btn = wx.Button(self, id, _("File..."))
        box.Add(btn, 0, wx.ALIGN_LEFT)
        self.Bind(wx.EVT_BUTTON, setter, btn)
        return (entry, box)
    
    def getMovieName(self):
        """Standard file browser for video file"""
        dlg = wx.FileDialog(self, message=_("Movie file"), style=wx.FD_OPEN)
        state = dlg.ShowModal()
        if state == wx.ID_OK:
            path = dlg.GetPath()
        else:
            path = None
        dlg.Destroy()
        return path
    
    def setLeftToFile(self, event):
        path = self.getMovieName()
        if path:
            self.left.SetValue(path)
    
    def setRightToFile(self, event):
        path = self.getMovieName()
        if path:
            self.right.SetValue(path)
    
    def getStoredList(self, name):
        """Retrieve most recent video source values for single entry"""
        s = app.config.Read(name + "List", "")
        if len(s) == 0:
            return []
        else:
            return s.split(';')
    
    def getStoredInt(self, name):
        """Retrieve which recent source was used last time"""
        s = app.config.Read(name + "Int", "")
        if len(s) == 0:
            return None
        else:
            return int(s)
    
    def storeList(self, key, entries):
        app.config.Write(key + "List", ';'.join(entries))
    
    def storeListEntry(self, key, path, keep=0):
        """Store the most recently selected/entered path,
           never overwriting first few entries if desired"""
        curr = self.getStoredList(key)
        # Add to recent URI list?
        if path not in curr:
            curr.insert(keep, path)
            if len(curr) > 8:
                curr = curr[0:8]
            app.config.Write(key + "List", ';'.join(curr))
        # Default for next time
        idx = curr.index(path)
        prev = self.getStoredInt(key)
        if idx != prev:
            app.config.Write(key + "Int", str(idx))

        
