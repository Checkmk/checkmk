#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Re-export from cmk.web for backward compatibility.
# All existing cmk.gui callers of cmk.gui.utils.html.HTML continue to work unchanged.
from cmk.web.utils.html import HTML as HTML
