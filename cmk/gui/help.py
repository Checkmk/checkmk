#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import cmk.gui.pages
from cmk.gui.globals import request, response, user


@cmk.gui.pages.register("ajax_switch_help")
def ajax_switch_help() -> None:
    state = request.var("enabled", "") != ""
    user.show_help = state
    response.set_data(json.dumps(state))
