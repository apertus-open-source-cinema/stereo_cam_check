#!/bin/bash          
echo Setting up paths  

# Read the current directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ] ; do SOURCE="$(readlink "$SOURCE")"; done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
export GST_PLUGIN_PATH=$DIR
export LD_LIBRARY_PATH=$DIR
export PYTHON_PATH=$DIR

echo Running StereoCamCheck
python main.py
