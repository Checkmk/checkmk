#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.gui import main_modules
from cmk.gui.plugins.wato.utils import rulespec_registry

main_modules.load_plugins()
sys.stdout.write(f"{'checkgroup_parameters:test' in rulespec_registry}\n")
