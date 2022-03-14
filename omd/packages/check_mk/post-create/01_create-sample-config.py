#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Initialize the Checkmk default configuration in case it is necessary.
"""
# pylint: disable=cmk-module-layer-violation
from cmk.gui import watolib
from cmk.gui import main_modules
from cmk.gui.utils.script_helpers import gui_context

if __name__ == "__main__":
    main_modules.load_plugins()
    with gui_context():
        watolib.init_wato_datastructures()
