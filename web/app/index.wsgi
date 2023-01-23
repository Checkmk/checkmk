#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui import log
from cmk.gui.wsgi.applications.utils import load_gui_log_levels

# Initialize logging as early as possible, before even importing most of the code.
log.init_logging()
log.set_log_levels(load_gui_log_levels())

from cmk.gui.wsgi.app import make_wsgi_app

DEBUG = False

if DEBUG:
    Application = make_wsgi_app(debug=True)
else:
    Application = make_wsgi_app()
    assert not Application.debug
    assert not Application.testing
