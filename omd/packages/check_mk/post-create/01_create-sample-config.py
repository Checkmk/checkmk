#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Initialize the Checkmk default configuration in case it is necessary.
"""
# pylint: disable=cmk-module-layer-violation
from cmk.gui import watolib
from cmk.gui.utils.script_helpers import application_and_request_context, initialize_gui_environment

if __name__ == '__main__':
    with application_and_request_context():
        initialize_gui_environment()
        watolib.init_wato_datastructures()
