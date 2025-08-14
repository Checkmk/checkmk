#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""When clicking on create dashboard, this page is opened to make the
context type of the new dashboard selectable."""

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.visuals.info import visual_info_registry


def page_create_dashboard(config: Config) -> None:
    visuals.page_create_visual("dashboards", list(visual_info_registry.keys()))
