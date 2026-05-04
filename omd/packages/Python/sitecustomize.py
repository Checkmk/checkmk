#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Make the site python know about the Checkmk specific python module paths

import os
import site
import sys
from pathlib import Path

# Set the Checkmk version specific python module directory. This is the
# location for the extra python modules shipped with Checkmk.
# NOTE: Modifying sys.path alone is not enough, site.addsitedir makes sure that
# path configuration files (*.pth) are actually found!
version_path = os.path.dirname(os.path.dirname(sys.executable))
site.addsitedir(version_path + "/lib/python3")


# Regular use case: When "omd" is being executed as root, we don't know
# anything about the site -> Only set the version specific directory.
omd_root = os.environ.get("OMD_ROOT")
if omd_root:
    # Set the site local python module directory. This is the place
    # for extension modules of the user, for example installed manually
    # or via pip.
    sys.path.insert(0, omd_root + "/local/lib/python3")

    # Block the import of modules that are not licensed for the current edition:
    from cmk.licensing.basics.finder import apply_feature_filter

    sys.meta_path[:] = apply_feature_filter(Path(omd_root), sys.meta_path)
