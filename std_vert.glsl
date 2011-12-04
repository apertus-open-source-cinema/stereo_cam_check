
// Bayer demosaic vertex shader
// Written by Morgan McGuire, Williams College
// From his paper "Efficient, High-Quality Bayer
// Demosaic Filtering on GPUs"

// DO NOT put #version here. The main app uses #define
// to generate different versions of this shader. The
// GLSL compiler complains if the version isn't first,
// so the app inserts version at the start

#ifdef DEBAYER
uniform vec4 sourceSize;    // w, h, 1/w, 1/h
uniform vec2 firstRed;      // First red pixel in Bayer pattern

varying vec4 center;
varying vec4 xCoord;
varying vec4 yCoord;
#endif

void main ()
{
    // Pass color
    gl_FrontColor = gl_Color;
#ifndef DEBAYER
    // Tex coords stay the same
    gl_TexCoord[0] = gl_MultiTexCoord0;
#else
    // Tex coord. Last two set to 0..sourceSize offset by firstRed
    center.xy = gl_MultiTexCoord0.st;
    center.zw = gl_MultiTexCoord0.st * sourceSize.st + firstRed;
    // X positions of adjacent texels
    vec2 invSize = sourceSize.zw;
    xCoord = center.x + vec4(-2.0 * invSize.x, -invSize.x,
                             invSize.x, 2.0 * invSize.x);
    // Y positions of adjacent texels
    yCoord = center.y + vec4(-2.0 * invSize.y, -invSize.y,
                             invSize.y, 2.0 * invSize.y);
#endif
    // Standard transform
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
