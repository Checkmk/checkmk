#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.gui import main_modules
from cmk.gui.watolib.config_domain_name import config_domain_registry

if errors := main_modules.get_failed_plugins():
    sys.exit(f"The following errors occurred during plug-in loading: {errors!r}")

sys.stdout.write(f"{'test' in config_domain_registry}\n")
