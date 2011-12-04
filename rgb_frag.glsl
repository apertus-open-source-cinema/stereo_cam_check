
// Straight use of texture as color

#version 120

uniform sampler2D image;

void main ()
{
    gl_FragColor = texture2D(image, gl_TexCoord[0].st);
}
