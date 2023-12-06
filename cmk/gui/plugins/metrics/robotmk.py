#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._utils import metric_info
from cmk.gui.i18n import _

metric_info["robotmk_suite_runtime"] = {
    "title": _("Suite runtime"),
    "unit": "s",
    "color": "34/a",
}

metric_info["robotmk_test_runtime"] = {
    "title": _("Test runtime"),
    "unit": "s",
    "color": "34/a",
}
