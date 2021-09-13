#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.debug import DebuggedApplication

import cmk.gui.log as log

log.init_logging()  # Initialize logging as early as possible

import cmk.gui.modules as modules
from cmk.gui.wsgi import make_app

modules.init_modules()

DEBUG = False

GUI_APP = make_app()

if DEBUG:
    Application = DebuggedApplication(GUI_APP, evalex=True, pin_security=False)
else:
    Application = GUI_APP
