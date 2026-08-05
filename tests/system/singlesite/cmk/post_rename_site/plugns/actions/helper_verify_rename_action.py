#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.post_rename_site.main import load_plugins
from cmk.post_rename_site.registry import rename_action_registry

load_plugins()

sys.stdout.write(f"{"test" in rename_action_registry}\n")
