#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.debug import DebuggedApplication

import cmk.gui.log as log
from cmk.gui.wsgi.applications.utils import load_gui_log_levels

# Initialize logging as early as possible
log.init_logging()
log.set_log_levels(load_gui_log_levels())

from cmk.gui import main_modules
from cmk.gui.wsgi import make_app

main_modules.load_plugins()

DEBUG = False

GUI_APP = make_app()

if DEBUG:
    Application = DebuggedApplication(GUI_APP, evalex=True, pin_security=False)
else:
    Application = GUI_APP
