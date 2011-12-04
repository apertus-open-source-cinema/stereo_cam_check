
#       Shader utility code
#       Written by Hugh Fisher, CECS ANU, 2011
#       Distributed under MIT/X11 license: see file COPYING

from __future__ import division, print_function


import OpenGL
from OpenGL import GL
from OpenGL.GL import *

_currentProgram = 0


def init():
    """Just test that we have GLSL"""
    try:
        glsl = glGetString(GL_SHADING_LANGUAGE_VERSION)
    except:
        glVers = glGetString(GL_VERSION)
        raise NotImplementedError("No shaders: OpenGL version: " + glVers)

def compileShader(kind, source, cppDefs=[]):
    """kind is VERTEX_SHADER etc. Source is string or list
       of strings, cppDefs is list of strings to prepend."""
    fullText = []
    for s in cppDefs:
        fullText.append(s + "\n")
    if not isinstance(source, list):
        fullText.append(source)
    else:
        fullText.extend(source)
    # Shader itself. I assume one per program
    shader = glCreateShader(kind)
    glShaderSource(shader, fullText)
    
    # Now compile and report any errors
    glCompileShader(shader)
    glGetShaderiv(shader, GL_COMPILE_STATUS);
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        msg = glGetShaderInfoLog(shader)
        raise RuntimeError("Compiling shader: " + msg)
    # Compiled OK doesn't mean perfect: might still fail link
    # with fragment shader when final program is created
    return shader

def loadShaderFile(kind, fileName, cppDefs=[]):
    """kind is VERTEX_SHADER etc. Source loaded from file"""
    f = open(fileName, 'r')
    src = f.read()
    # And build shader
    result = compileShader(kind, src, cppDefs)
    f.close()
    return result

def newProgram(vert, frag, geom=None):
    """Create program from shaders."""
    if not vert and not frag and not geom:
        raise RuntimeError("newShaderProgram without any shaders!");

    prog = glCreateProgram()
    if vert:
        glAttachShader(prog, vert)
    if frag:
        glAttachShader(prog, frag)
    if geom:
        glAttachShader(prog, geom)
    # Now check they play nice with each other 
    glLinkProgram(prog)
    if not glGetProgramiv(prog, GL_LINK_STATUS):
        msg = glGetProgramInfoLog(prog)
        raise RuntimeError("Linking shaders: " + msg)
    glValidateProgram(prog)
    if not glGetProgramiv(prog, GL_VALIDATE_STATUS):
        msg = glGetProgramInfoLog(prog)
        raise RuntimeError("Validating program: " + msg)
    # Make current: this is handy for setting up uniforms etc
    useProgram(prog)
    
    return prog

def useProgram(program):
    """Install program, or zero to return to fixed pipeline"""
    global _currentProgram
    #
    # Zero is allowed: means turn off shaders
    glUseProgram(program)
    _currentProgram = program

def getProgram():
    return _currentProgram

def getUniform(program, name):
    """Return handle to program uniform var with given name"""
    h = glGetUniformLocation(program, name)
    if h < 0:
        raise RuntimeError(name + ": No such uniform in shader")
    return h
