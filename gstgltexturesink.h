#ifndef __GST_GLTEXTURESINK_H__
#define __GST_GLTEXTURESINK_H__

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

#include <gst/gst.h>
#include <gst/base/gstbasesink.h>
#include <gst/video/video.h>

G_BEGIN_DECLS

/* #defines don't like whitespacey bits */
#define GST_TYPE_GLTEXTURESINK \
    (gst_gltexture_sink_get_type())
#define GST_GLTEXTURESINK(obj) \
    (G_TYPE_CHECK_INSTANCE_CAST((obj),GST_TYPE_GLTEXTURESINK,GstGLTextureSink))
#define GST_GLTEXTURESINK_CLASS(klass) \
    (G_TYPE_CHECK_CLASS_CAST((klass),GST_TYPE_GLTEXTURESINK,GstGLTextureSinkClass))
#define GST_IS_GLTEXTURESINK(obj) \
    (G_TYPE_CHECK_INSTANCE_TYPE((obj),GST_TYPE_GLTEXTURESINK))
#define GST_IS_GLTEXTURESINK_CLASS(klass) \
    (G_TYPE_CHECK_CLASS_TYPE((klass),GST_TYPE_GLTEXTURESINK))

typedef struct _GstGLTextureSink      GstGLTextureSink;
typedef struct _GstGLTextureSinkClass GstGLTextureSinkClass;


/*  IMPORTANT: This plugin can NOT be used from gst-launch. It uploads
    data to an OpenGL texture map, so the client program must have a
    GLXContext with associated X display and drawables.
*/

/*
    PROPERTIES
    
    texture     Required. The OpenGL texture id which will be updated.
                Since this plugin is designed for use by OpenGL coders
                embedding GST in their apps, it's reasonable to expect
                that the coder knows about glGenTextures.
                
                When the texture property is assigned, this plugin also
                grabs the current GLXContext for later use.
    
    texture_format The OpenGL texture format to use. Defaults to GL_RGB
                unless the source is grayscale
    
    width, height   (Read only) Pixel dimensions of video source
    
    is_bayer    (Read only) True if source data is Bayer mosaic
*/

struct _GstGLTextureSink
{
    GstBaseSink base;
    /* Properties */
    guint       texture;
    guint       texture_format;
    guint       width;              /* Of video, not texture */
    guint       height;
    gboolean    is_bayer;
    /* Internal state */
    Display *   dpy;
    GLXContext  context;
    GLXDrawable xDraw;
    int         srcFormat;          /* OpenGL version of source format */
    int         texW, texH;
    /* Most recent frame. We can't upload buffers to the OpenGL
       texture without a valid context, this is the most recently
       'rendered' frame for use by code that actually does glTexImage. */
    GstBuffer * currentFrame;
    int         fw, fh;
    guint       callbackTag;
};

struct _GstGLTextureSinkClass 
{
    GstBaseSinkClass parent_class;
};

GType gst_gltexture_sink_get_type(void);

G_END_DECLS

#endif
