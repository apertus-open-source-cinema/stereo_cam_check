

#       Construct GStreamer source pipeline
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING

from __future__ import division, print_function

import wx

import pygst
pygst.require("0.10")
import gst

from app import _

import gstgltexturesink

_pngPipe    = "filesrc location={source} ! pngdec "
_jpegPipe   = "filesrc location={source} ! jpegdec ! ffmpegcolorspace"
# Old pipe for non-Bayer
#_rtspPipe   = "rtspsrc location={source} ! decodebin ! ffmpegcolorspace "
# Pipe for Elphel Bayer stream
_rtspPipe   = "rtspsrc location={source} latency=50 ! rtpjpegdepay ! jpegdec ! queue ! jp462bayer "
_moviePipe  = "filesrc location={source} ! decodebin ! ffmpegcolorspace "

def defaultPipes():
    return [ _moviePipe, _rtspPipe, _pngPipe, ]

def defaultPipeline(source):
    if source.endswith(".png"):
        return _pngPipe
    elif source.endswith(".jpg") or source.endswith(".jpeg"):
        return _jpegPipe
    elif source.startswith("rtsp:"):
        return _rtspPipe
    else:
        return _moviePipe

def configSink(glSink, pipeline):
    """Apply any glTextureSink parameters to sink object
       and strip that component from the string"""
    gstComponents = pipeline.split('!')
    final = gstComponents[-1].strip()
    if final.startswith("gstgltexturesink"):
        # Since we've already created the sink, remove from
        # string that will be used to build video source
        del gstComponents[-1]
        # But apply any parameter specs requested by user
        params = final.split()[1:]
        for p in params:
            p = p.strip()
            try:
                name,value=p.split('=')
                glSink.set_property(name, eval(value))
            except:
                wx.MessageBox(_("Cannot set property on GLTextureSink\n") + p,
                      _("Error creating GST pipeline"),
                      wx.OK | wx.ICON_ERROR, None)
    return '!'.join(gstComponents)

def createPipeline(source, pipeline):
    """GStreamer pipeline that generates video"""
    # Replace {source} in pipeline string with actual source
    pipeline = pipeline.format(source=source)
    try:
        pipe = gst.parse_launch(pipeline)
    except:
        wx.MessageBox(_("Unable to create GStreamer pipeline\n") +
                      pipeline + "\n" +
                      _("Suggest testing with gst-launch"),
                      _("Error creating GST pipeline"),
                      wx.OK | wx.ICON_ERROR, None)
        raise RuntimeError("Unable to create GStreamer pipeline " + pipeline)
    #
    return pipe


    
