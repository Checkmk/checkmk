#!/usr/bin/env bash

function install(){
    echo "Installing Forecast Graphs dependencies..."
    # Install dependecies
    pip install pystan
    LIBRARY_PATH=${OMD_ROOT}/lib:${LIBRARY_PATH} pip install subprocess32
    LIBRARY_PATH=${OMD_ROOT}/lib:${LIBRARY_PATH} pip install fbprophet
    pip uninstall -y matplotlib

    # Cleanup of unnecessary files
    rm -rf local/lib/python/fbprophet/tests
    rm -rf local/lib/python/pandas/tests
    rm -rf local/lib/python/numpy/tests
    rm -rf local/lib/python/numpy/distutils/tests
    rm -rf local/lib/python/numpy/fft/tests
    rm -rf local/lib/python/numpy/f2py/tests
    rm -rf local/lib/python/numpy/ma/tests
    rm -rf local/lib/python/numpy/linalg/tests
    rm -rf local/lib/python/numpy/polynomial/tests
    rm -rf local/lib/python/numpy/random/tests
    rm -rf local/lib/python/numpy/testing/tests
    rm -rf local/lib/python/numpy/lib/tests
    rm -rf local/lib/python/numpy/core/tests
    rm -rf local/lib/python/numpy/compat/tests
    rm -rf local/lib/python/numpy/matrixlib/tests
    rm -rf local/lib/python/matplotlib/tests
    rm -rf local/lib/python/matplotlib/sphinxext/tests
    rm -rf local/lib/python/Cython/Debugger/Tests
    rm -rf local/lib/python/Cython/Build/Tests
    rm -rf local/lib/python/Cython/Compiler/Tests
    rm -rf local/lib/python/Cython/Tests
    rm -rf local/lib/python/mpl_toolkits/tests
    rm -rf local/lib/python/pystan/stan/src/test
    rm -rf local/lib/python/pystan/stan/lib/stan_math/test
    rm -rf local/lib/python/pystan/tests
    rm -rf local/lib/python/pystan/stan/lib/stan_math/make/tests

    # Restart apache
    omd restart apache
}

function uninstall(){
    echo "Removing Forecast Graphs dependencies"
    pip install pip-autoremove
    local/lib/python/bin/pip-autoremove fbprophet  pystan -y
    pip uninstall -y pip-autoremove

    omd restart apache
}

DOC="Install script for Forecast Graphs dependencies
usage: $0 [OPTION]

OPTION:
                        default: Install dependencies
  -u, --uninstall       Remove installed dependencies
  -h, --help            Show this help
"
case $1 in
    -u|--uninstall)
        uninstall
        ;;
    -h|--help)
        echo "$DOC"
        ;;

    *)
        install
esac
