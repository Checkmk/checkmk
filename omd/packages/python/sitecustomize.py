#!/usr/bin/env python
# Make the site python know about the Check_MK specific python module paths

import sys, os

# Set the Check_MK version specific python module directory. This is
# the location for the extra python modules shipped with Check_MK.
version_path = os.path.dirname(os.path.dirname(sys.executable))
sys.path.insert(0, version_path + "/lib/python")

# Regular use case: When "omd" is being executed as root, we don't know
# anything about the site -> Only set the version specific directory.
omd_root = os.environ.get("OMD_ROOT")
if omd_root:
    # Set the site local python module directory. This is the place
    # for extension modules of the user, for example installed manually
    # or via pip.
    sys.path.insert(0, omd_root + "/local/lib/python")
