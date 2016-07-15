#!/bin/bash

# this is run from active checks with empty environment, so we somehow need to figure out
# where python, the passwordstore.py and the passwordstore itself reside

OMD_ROOT=$1
shift

export PYTHONPATH=$OMD_ROOT/lib/python:$OMD_ROOT/local/lib/python

$OMD_ROOT/bin/python $OMD_ROOT/lib/python/cmk/passwordstore.py\
    --get $1 --user $2\
    --keydir $OMD_ROOT/var/check_mk/private_keys\
    --file $OMD_ROOT/var/check_mk/passwords.json

