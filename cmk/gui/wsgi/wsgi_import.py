#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Initializes Apache python environments before processing HTTP requests

This script is called as WSGIImportScript when an application server process starts. It's called
before a request can be handled by the process, so it should not slow down the single HTTP requests.

https://modwsgi.readthedocs.io/en/develop/configuration-directives/WSGIImportScript.html
"""

from cmk.gui import main_modules

main_modules.load_plugins()
