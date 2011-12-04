
// Video shader. Texture map is used as source
// color, variants for doing red-blue stereo
// and TODO de-Bayering

// Possible defines:
// #define ANAGLYPH     for red-blue stereo
// #define DEBAYER      for textures in Bayer form

// DO NOT put #version here. The main app uses #define
// to generate different versions of this shader. The
// GLSL compiler complains if the version isn't first,
// so the app inserts version at the start

uniform sampler2D image;

#ifdef DEBAYER
varying vec4 center;
varying vec4 xCoord;
varying vec4 yCoord;
#endif

void main ()
{
    vec4  rgb;

#ifndef DEBAYER
    // Easy
    rgb = texture2D(image, gl_TexCoord[0].st);
#else
    // Bayer demosaic fragment shader
    // Written by Morgan McGuire, Williams College
    // From his paper "Efficient, High-Quality Bayer
    // Demosaic Filtering on GPUs"
    #define fetch(x, y) texture2D(image, vec2((x), (y))).r
    
    float C = texture2D(image, center.xy).r;
    const vec4 kC = vec4(4.0, 6.0, 5.0, 5.0) / 8.0;
    
    // Determine which of 4 elements in mosaic we are
    vec2 alternate = mod(floor(center.zw), 2.0);
    
    vec4 Dvec = vec4(
        fetch(xCoord[1], yCoord[1]),    // (-1, -1)
        fetch(xCoord[1], yCoord[2]),    // (-1, 1)
        fetch(xCoord[2], yCoord[1]),    // (1, -1)
        fetch(xCoord[2], yCoord[2]));   // (1, 1)
    
    vec4 PATTERN = (kC.xyz * C).xyzz;
    
    Dvec.xy += Dvec.zw;
    Dvec.x  += Dvec.y;
    
    vec4 value = vec4(
        fetch(center.x, yCoord[0]),     // (0, -2)
        fetch(center.x, yCoord[1]),     // (0, -1)
        fetch(xCoord[0], center.y),     // (-1, 0)
        fetch(xCoord[1], center.y));    // (-2, 0)
    
    vec4 temp = vec4(
        fetch(center.x, yCoord[3]),     // (0, 2)
        fetch(center.x, yCoord[2]),     // (0, 1)
        fetch(xCoord[3], center.y),     // (2, 0)
        fetch(xCoord[2], center.y));    // (1, 0)
    value += temp;
    
    const vec4 kA = vec4(-1.0, -1.5,  0.5, -1.0) / 8.0;
    const vec4 kB = vec4( 2.0,  0.0,  0.0,  4.0) / 8.0;
    const vec4 kD = vec4( 0.0,  2.0, -1.0, -1.0) / 8.0;
    #define kE (kA.xywz)
    #define kF (kB.xywz)
    
    // There are five filter patterns: identity, cross,
    // checker, theta, phi. Precompute them all
    #define A (value[0])
    #define B (value[1])
    #define D (Dvec[0])
    #define E (value[2])
    #define F (value[3])
    
    // Avoid zero elements
    PATTERN.yzw += (kD.yz * D).xyy;
    
    PATTERN += (kA.xyz * A).xyzx + (kE.xyw * E).xyxz;
    PATTERN.xw += kB.xw * B;
    PATTERN.xz += kF.xz * F;
    
    rgb = (alternate.y == 0) ?
                ((alternate.x == 0) ?
                    vec4(C, PATTERN.xy, 1) :
                    vec4(PATTERN.z,C, PATTERN.w, 1)) :
                ((alternate.x == 0) ?
                    vec4(PATTERN.w, C, PATTERN.z, 1) :
                    vec4(PATTERN.yx, C, 1));
    rgb = clamp(rgb, 0.0, 1.0);
#endif

#ifdef ANAGLYPH
    // Convert to grayscale intensity
    float i = 0.2125 * rgb.r + 0.71546 * rgb.g + 0.0721 * rgb.b;
    rgb = vec4(i, i, i, 1);
#endif
    
    gl_FragColor = rgb;
}
