
/*
Copyright (c) 2011 Hugh Fisher, CECS, ANU

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the
Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall
be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

/*  TODO: Implement de-Bayering on GPU within this plugin */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <limits.h>
#include <string.h>

#include <gst/gst.h>

#include <GL/gl.h>
#include <GL/glx.h>

#ifdef EMBEDDED_PYTHON
#include <Python.h>
#endif

#include "gstgltexturesink.h"

GST_DEBUG_CATEGORY_STATIC(gst_gltexture_sink_debug);
#define GST_CAT_DEFAULT gst_gltexture_sink_debug


enum
{
    PROP_0,
    PROP_TEXTURE,
    PROP_TEXTURE_FORMAT,
    PROP_WIDTH,
    PROP_HEIGHT,
    PROP_IS_BAYER,
};

static GstStaticPadTemplate sink_factory = GST_STATIC_PAD_TEMPLATE(
    "sink",
    GST_PAD_SINK,
    GST_PAD_ALWAYS,
    GST_STATIC_CAPS(
        /* RGB video. OpenGL can't handle alpha/pad in upper byte */
        GST_VIDEO_CAPS_RGBx ";"
        GST_VIDEO_CAPS_BGRx ";"
        GST_VIDEO_CAPS_RGBA ";"
        GST_VIDEO_CAPS_BGRA ";"
        GST_VIDEO_CAPS_RGB  ";"
        GST_VIDEO_CAPS_BGR  ";"
        /* Greyscale video */
        "video/x-raw-gray,bpp=(int)8,depth=(int)8,"
        "width="GST_VIDEO_SIZE_RANGE",height="GST_VIDEO_SIZE_RANGE
        ",framerate="GST_VIDEO_FPS_RANGE    ";"
        /* Bayer raw video */
        "video/x-raw-bayer,bpp=(int)8,depth=(int)8,"
        "width="GST_VIDEO_SIZE_RANGE",height="GST_VIDEO_SIZE_RANGE
        ",framerate="GST_VIDEO_FPS_RANGE    ";"
    )
);

GST_BOILERPLATE(GstGLTextureSink, gst_gltexture_sink,
                GstBaseSink, GST_TYPE_BASE_SINK);

static void gst_gltexture_sink_set_property(GObject * object, guint prop_id,
                    const GValue * value, GParamSpec * pspec);
static void gst_gltexture_sink_get_property(GObject * object, guint prop_id,
                    GValue * value, GParamSpec * pspec);

static gboolean gst_gltexture_sink_setcaps(GstPad * pad, GstCaps * caps);
static void gst_gltexture_sink_get_times(GstBaseSink * base, GstBuffer * buf,
                    GstClockTime * start, GstClockTime * finish);
static GstStateChangeReturn gst_gltexture_sink_change_state(
                GstElement * element, GstStateChange transition);
static GstFlowReturn gst_gltexture_sink_preroll(GstBaseSink * self, GstBuffer * buffer);
static GstFlowReturn gst_gltexture_sink_render(GstBaseSink * self, GstBuffer * buffer);

#define GLTextureSinkDescription \
          "Upload video to OpenGL texture map"

static void gst_gltexture_sink_base_init(gpointer gclass)
{
    GstElementClass *element_class = GST_ELEMENT_CLASS(gclass);

    gst_element_class_add_pad_template(element_class,
            gst_static_pad_template_get(&sink_factory));
            
    gst_element_class_set_details_simple(element_class,
      "GLTextureSink",
      "Sink/Video",
      GLTextureSinkDescription,
      "Hugh Fisher <hugh.fisher@anu.edu.au>");
}

static void gst_gltexture_sink_class_init(GstGLTextureSinkClass * klass)
{
    GObjectClass *      gobject_class;
    GstElementClass *   gstelement_class;
    GstBaseSinkClass *  gstbasesink_class;

    gobject_class = (GObjectClass *)klass;
    gstelement_class = (GstElementClass *)klass;
    gstbasesink_class = (GstBaseSinkClass *)klass;

    gobject_class->set_property = gst_gltexture_sink_set_property;
    gobject_class->get_property = gst_gltexture_sink_get_property;

    g_object_class_install_property(gobject_class, PROP_TEXTURE,
            g_param_spec_uint("texture", "Texture", "OpenGL Texture id",
            0, UINT_MAX, 0, G_PARAM_READWRITE));
    g_object_class_install_property(gobject_class, PROP_TEXTURE_FORMAT,
            g_param_spec_uint("texture_format", "Texture Format", "OpenGL internal texture format",
            0, UINT_MAX, 0, G_PARAM_READWRITE));
    g_object_class_install_property(gobject_class, PROP_WIDTH,
            g_param_spec_uint("width", "Width", "Video source width",
            0, UINT_MAX, 0, G_PARAM_READABLE));
    g_object_class_install_property(gobject_class, PROP_HEIGHT,
            g_param_spec_uint("height", "Height", "Video source height",
            0, UINT_MAX, 0, G_PARAM_READABLE));
    g_object_class_install_property(gobject_class, PROP_IS_BAYER,
            g_param_spec_boolean("is_bayer", "Is Bayer", "Source data is Bayer",
            FALSE, G_PARAM_READABLE));
    
    gstelement_class->change_state = GST_DEBUG_FUNCPTR(gst_gltexture_sink_change_state);
    gstbasesink_class->preroll   = GST_DEBUG_FUNCPTR(gst_gltexture_sink_preroll);
    gstbasesink_class->render    = GST_DEBUG_FUNCPTR(gst_gltexture_sink_render);
    gstbasesink_class->get_times = GST_DEBUG_FUNCPTR(gst_gltexture_sink_get_times);
}

static void gst_gltexture_sink_init(GstGLTextureSink * self,
                    GstGLTextureSinkClass * gclass)
{
    GstPad * pad;
    
    pad = GST_BASE_SINK_PAD(self);
    gst_pad_set_setcaps_function(pad, gst_gltexture_sink_setcaps);
    
    self->texture   = 0;
    self->texture_format = 0;
    self->width     = 0;
    self->height    = 0;
    self->is_bayer  = FALSE;
    
    self->dpy       = 0;
    self->context   = NULL;
    self->xDraw     = 0;
    self->srcFormat = 0;
    self->texW      = 0;
    self->texH      = 0;
    
    self->currentFrame = NULL;
    self->callbackTag  = 0;
}

static gboolean gltexturesink_init(GstPlugin * gltexturesink)
{
    GST_DEBUG_CATEGORY_INIT(gst_gltexture_sink_debug, "gltexturesink",
                0, GLTextureSinkDescription);

    return gst_element_register(gltexturesink,
            "gltexturesink",
            GST_RANK_NONE,
            GST_TYPE_GLTEXTURESINK);
}

/* GST_PLUGIN_DEFINE needs PACKAGE to be defined. */
#ifndef PACKAGE
#define PACKAGE "GLTextureSink"
#endif

GST_PLUGIN_DEFINE(
    GST_VERSION_MAJOR,
    GST_VERSION_MINOR,
    "gltexturesink",
    GLTextureSinkDescription,
    gltexturesink_init,
    VERSION,
    "MIT/X11",
    "None",
    "http://cs.anu.edu.au/~hugh.fisher/2dstuff"
)


static void gltxs_saveCurrentContext(GstGLTextureSink * self)
{
    self->dpy     = glXGetCurrentDisplay();
    self->context = glXGetCurrentContext();
    self->xDraw   = glXGetCurrentDrawable();
}

static void gst_gltexture_sink_set_property(GObject * object, guint prop_id,
                    const GValue * value, GParamSpec * pspec)
{
    GstGLTextureSink * self = GST_GLTEXTURESINK(object);

    switch (prop_id) {
        case PROP_TEXTURE:
            self->texture = g_value_get_uint(value);
            gltxs_saveCurrentContext(self);
            break;
        case PROP_TEXTURE_FORMAT:
            self->texture_format = g_value_get_uint(value);
            break;
      default:
            G_OBJECT_WARN_INVALID_PROPERTY_ID(object, prop_id, pspec);
            break;
    }
}

static void gst_gltexture_sink_get_property(GObject * object, guint prop_id,
                    GValue * value, GParamSpec * pspec)
{
    GstGLTextureSink *self = GST_GLTEXTURESINK(object);

    switch (prop_id) {
        case PROP_TEXTURE:
            g_value_set_uint(value, self->texture);
            break;
        case PROP_TEXTURE_FORMAT:
            g_value_set_uint(value, self->texture_format);
            break;
        case PROP_WIDTH:
            g_value_set_uint(value, self->width);
            break;
        case PROP_HEIGHT:
            g_value_set_uint(value, self->height);
            break;
        case PROP_IS_BAYER:
            g_value_set_boolean(value, self->is_bayer);
            break;
        default:
            G_OBJECT_WARN_INVALID_PROPERTY_ID(object, prop_id, pspec);
            break;
    }
}

static GLint gltxs_GstFormatToGL (GstCaps * caps)
{
    const gchar *   mimeType;
    GstVideoFormat  gstFormat;
    gint            w, h;
    
    mimeType = gst_structure_get_name(gst_caps_get_structure(caps, 0));
    
    if (strcmp(mimeType, "video/x-raw-gray") == 0) {
        return GL_LUMINANCE;
    } else if (strcmp(mimeType, "video/x-raw-bayer") == 0) {
        return GL_LUMINANCE;
    } else if (strcmp(mimeType, "video/x-raw-rgb") == 0) {
        gst_video_format_parse_caps(caps, &gstFormat, &w, &h);
        if (gstFormat == GST_VIDEO_FORMAT_RGBx)
            return GL_RGBA;
        else if (gstFormat == GST_VIDEO_FORMAT_BGRx)
            return GL_BGRA;
        else if (gstFormat == GST_VIDEO_FORMAT_RGBA)
            return GL_RGBA;
        else if (gstFormat == GST_VIDEO_FORMAT_BGRA)
            return GL_BGRA;
        else if (gstFormat == GST_VIDEO_FORMAT_RGB)
            return GL_RGB;
        else if (gstFormat == GST_VIDEO_FORMAT_BGR)
            return GL_BGR;
        else
            return 0;
    } else
        return 0;
}

/*  To initialize or update an OpenGL texture, we need a GLXContext.
    Since the Gst pipeline executes asynchronously from the main
    event loop, we can't rely on the context being current and
    setting the context fails randomly (at least on my system).
    
    My solution is for the preroll/render to save the buffer contents
    and use g_idle_add for for a one-shot callback to actually do
    something. There's a possibility that a frame will get overwritten
    before the idle callback executes, but I don't think it's worth
    worrying about, it's equivalent to dropping frames under load */

static void gltxs_saveBuffer(GstGLTextureSink * self, GstBuffer * buf, int w, int h)
{
    GstBuffer * prev;
    
    prev = self->currentFrame;
    gst_buffer_ref(buf);
    self->currentFrame = buf;
    self->fw = w;
    self->fh = h;
    if (prev) {
        /* We're decoding faster than window updating? */
        /* g_debug("GLTextureSink: decode overrun detected"); */
        gst_buffer_unref(prev);
    }
}

static gboolean gltxs_initTexture(GstGLTextureSink * self)
{
    /* Used in PREROLL. Would also be necessary if the
       video source size changes during execution. */

    if (self->texture == 0) {
        g_warning("GLTextureSink: No texture ID");
        return FALSE;
    }
    
    if (! glXMakeContextCurrent(self->dpy, self->xDraw, self->xDraw, self->context)) {
        g_warning("GLTextureSink: glXMakeContextCurrent");
        return FALSE;
    }
    self->width = self->fw;
    self->height = self->fh;
    
    if (strstr((char *)glGetString(GL_EXTENSIONS), "GL_ARB_texture_non_power_of_two")) {
        self->texW = self->width;
        self->texH = self->height;
    } else {
        /* Ancient graphics card. Nearest power of 2 dimensions */
        g_warning("Ancient OpenGL detected: rounding dimensions to power of 2");
        self->texW = 2;
        while (self->texW < self->width)
            self->texW *= 2;
        self->texH = 2;
        while (self->texH < self->height)
            self->texH *= 2;
    }
    /* Initialize empty */
    glBindTexture(GL_TEXTURE_2D, self->texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
    /* Bayer demosaic relies on not blending */
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    
    /* Video data may not be nicely aligned */
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    
    glTexImage2D(GL_TEXTURE_2D, 0, self->texture_format,
                self->texW, self->texH, 0,
                self->texture_format, GL_UNSIGNED_BYTE, NULL);
    
    /* And upload first frame */
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0,
            self->fw, self->fh, self->srcFormat,
            GL_UNSIGNED_BYTE, GST_BUFFER_DATA(self->currentFrame));
       
    gst_buffer_unref(self->currentFrame);
    self->currentFrame = NULL;
    self->callbackTag  = 0;

    return FALSE;
}

static gboolean gltxs_updateTexture(GstGLTextureSink * self)
{
    /* Used to RENDER frame, by uploading to OpenGL */
    if (self->texture == 0) {
        g_error("GLTextureSink: No texture ID");
        return FALSE;
    }
    
    if (! glXMakeContextCurrent(self->dpy, self->xDraw, self->xDraw, self->context)) {
        g_error("GLTextureSink: glXMakeContextCurrent");
        /* Hope it was just transient, try again by return True? */
        return FALSE;
    }
    
    if (self->currentFrame == NULL) {
        g_error("GLTextureSink: NULL currentFrame");
        return FALSE;
    }
    
    glBindTexture(GL_TEXTURE_2D, self->texture);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0,
            self->fw, self->fh, self->srcFormat,
            GL_UNSIGNED_BYTE, GST_BUFFER_DATA(self->currentFrame));
    
    gst_buffer_unref(self->currentFrame);
    self->currentFrame = NULL;
    self->callbackTag  = 0;
    
    return FALSE;
}

static gboolean gst_gltexture_sink_setcaps(GstPad * pad, GstCaps * caps)
{
    /* This rejects YUV or similar formats. */
    if (gltxs_GstFormatToGL(caps) > 0)
        return TRUE;
    else
        return FALSE;
}

static void gst_gltexture_sink_get_times(GstBaseSink * base, GstBuffer * buf,
                    GstClockTime * start, GstClockTime * finish)
{
    /* Not sure what this does. aasink has one, so it
       seemed like a good idea to copy it here */
    *start  = GST_BUFFER_TIMESTAMP(buf);
    *finish = *start + GST_BUFFER_DURATION(buf);
}

static GstStateChangeReturn gst_gltexture_sink_change_state(
                GstElement * element, GstStateChange transition)
{
    GstGLTextureSink *  self;

    self = GST_GLTEXTURESINK(element);

    if (transition == GST_STATE_CHANGE_READY_TO_NULL) {
        if (self->callbackTag > 0)
            g_source_remove(self->callbackTag);
    }
    return GST_ELEMENT_CLASS(parent_class)->change_state(element, transition);
}

static GstFlowReturn gst_gltexture_sink_preroll(GstBaseSink * base, GstBuffer * buf)
{
    GstGLTextureSink *  self;
    GstCaps *           caps;
    const gchar *       mimeType;
    GstVideoFormat      format;
    gint                w, h;
    
    if (GST_BUFFER_SIZE(buf) <= 0)
        return GST_FLOW_OK;
        
    self = GST_GLTEXTURESINK(base);

    caps = gst_buffer_get_caps(buf);
    self->srcFormat = gltxs_GstFormatToGL(caps);
    if (self->texture_format == 0) {
        self->texture_format = self->srcFormat;
    }
    
    mimeType = gst_structure_get_name(gst_caps_get_structure(caps, 0));
    if (strcmp(mimeType, "video/x-raw-bayer") == 0) {
        self->is_bayer = TRUE;
    }
    
    gst_video_format_parse_caps(caps, &format, &w, &h);
    gltxs_saveBuffer(self, buf, w, h);

    self->callbackTag = g_idle_add_full(G_PRIORITY_HIGH_IDLE,
                            (GSourceFunc)gltxs_initTexture, self, NULL);

    return GST_FLOW_OK;
}

static GstFlowReturn gst_gltexture_sink_render(GstBaseSink * base, GstBuffer * buf)
{
    GstGLTextureSink *  self;
    GstCaps *           caps;
    GstVideoFormat      format;
    gint                w, h;
    
    if (GST_BUFFER_SIZE(buf) <= 0)
        return GST_FLOW_OK;
    
    self = GST_GLTEXTURESINK(base);
    
    caps = gst_buffer_get_caps(buf);
    gst_video_format_parse_caps(caps, &format, &w, &h);
    /* printf("Render %d x %d = %d bytes\n", w, h, GST_BUFFER_SIZE(buf)); */
    gltxs_saveBuffer(self, buf, w, h);
    if (self->callbackTag == 0)
        self->callbackTag = g_idle_add_full(G_PRIORITY_HIGH_IDLE,
                            (GSourceFunc)gltxs_updateTexture, self, NULL);

    return GST_FLOW_OK;
}

/* For use as Python module */
#ifdef EMBEDDED_PYTHON
void initgstgltexturesink(void)
{
    GstRegistry *   gstDefault;
    GstPlugin *     self;
    GError *        err = NULL;
    char            msg[512];
    
    gstDefault = gst_registry_get_default();
    
    self = gst_plugin_load_file("gstgltexturesink.so", &err);
    if (self == NULL) {
        snprintf(msg, sizeof(msg), "Failed to load plugin: %s", err->message);
        PyErr_SetString(PyExc_RuntimeError, msg);
        PyErr_Print();
        return;
    }
    gst_registry_add_plugin(gstDefault, self);
    Py_InitModule3("gstgltexturesink", NULL, "GST GLTextureSink plugin");
}
#endif


