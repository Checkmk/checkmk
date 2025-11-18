#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sys

from cmk.gui import main_modules
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context

if errors := main_modules.get_failed_plugins():
    sys.exit(f"The following errors occurred during plug-in loading: {errors!r}")

with gui_context():
    print(
        json.dumps(
            [
                f"{gui_part}/{plugin_file}: {error}"
                for _path, gui_part, plugin_file, error in get_failed_plugins()
            ]
        )
    )
