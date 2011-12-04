
#       App preferences, recent config, internationalization
#       for stereo camera preview
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING

from __future__ import division, print_function

import os

import wx

# The app config needs to be a singleton

config = wx.Config("StereoCamCheck", "HughFisher")

# Allow translation into other languages

try:
    locale = wx.Locale(wx.LANGUAGE_DEFAULT)
    locale.AddCatalogLookupPathPrefix(os.path.join(os.getcwd(), "locale"))
    locale.AddCatalog('scc')
    def _(T): return wx.GetTranslation(T)
except:
    def _T(): return T
