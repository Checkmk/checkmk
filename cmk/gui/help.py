#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageEndpoint, PageRegistry


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_switch_help", ajax_switch_help))


def ajax_switch_help(config: Config) -> None:
    state = request.var("enabled", "") != ""
    user.inline_help_as_text = state
    response.set_data(json.dumps(state))
