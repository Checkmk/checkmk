#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.ccc.version import edition
from cmk.gui import main_modules
from cmk.gui.graphing._from_api import metrics_from_api
from cmk.utils import paths

main_modules.register(edition(paths.omd_root))

if errors := main_modules.get_failed_plugins():
    sys.exit(f"The following errors occurred during plug-in loading: {errors!r}")

sys.stdout.write(f"{'metric_int_test' in metrics_from_api}\n")
