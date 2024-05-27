#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pwd
import re
import sys
from pathlib import Path

from omdlib.users_and_groups import group_exists, user_exists
from omdlib.utils import site_exists


def site_name_from_uid() -> str:
    return pwd.getpwuid(os.getuid()).pw_name


# Bail out if name for new site is not valid (needed by create/mv/cp)
def sitename_must_be_valid(site_name: str, site_dir: Path, reuse: bool = False) -> None:
    # Make sanity checks before starting any action

    if not re.match("^[a-zA-Z_][a-zA-Z_0-9]{0,15}$", site_name):
        sys.exit(
            "Invalid site name. Must begin with a character, may contain characters, digits and _ and have length 1 up to 16"
        )

    if not reuse and site_exists(site_dir):
        sys.exit("Site '%s' already existing." % site_name)
    if not reuse and group_exists(site_name):
        sys.exit("Group '%s' already existing." % site_name)
    if not reuse and user_exists(site_name):
        sys.exit("User '%s' already existing." % site_name)
