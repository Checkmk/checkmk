#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib3

from cmk.gui.utils import load_web_plugins

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_watolib_plugins() -> None:
    load_web_plugins("watolib", globals())
