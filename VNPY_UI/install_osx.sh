#!/usr/bin/env bash

python=$1
shift 1

[[ -z $python ]] && python=python

$python -m pip install --upgrade pip wheel

# Get and build ta-lib
function install-ta-lib()
{
    export HOMEBREW_NO_AUTO_UPDATE=true
    brew install ta-lib
}
function ta-lib-exists()
{
    ta-lib-config --libs > /dev/null
}
ta-lib-exists || install-ta-lib

# install ta-lib
$python -m pip install numpy==1.21.5
$python -m pip install ta-lib==0.4.24

# degrade setuptools to install deap 1.3.1 for python3.10 
$python -m pip install setuptools==57.0.0

# Install Python Modules
$python -m pip install -r requirements.txt

# Install VeighNa
$python -m pip install . $@