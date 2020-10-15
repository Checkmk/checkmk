#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.http import Request

from cmk.gui.utils.url_encoder import URLEncoder


def requested_file_name(request: Request) -> str:
    parts = request.requested_file.rstrip("/").split("/")

    if len(parts) == 3 and parts[-1] == "check_mk":
        # Load index page when accessing /[site]/check_mk
        file_name = "index"

    elif parts[-1].endswith(".py"):
        # Regular pages end with .py - Stript it away to get the page name
        file_name = parts[-1][:-3]
        if file_name == "":
            file_name = "index"

    else:
        file_name = "index"

    return file_name


def makeuri_contextless(
    request: Request,
    vars_: HTTPVariables,
    filename: Optional[str] = None,
) -> str:
    if not filename:
        filename = requested_file_name(request) + '.py'
    if vars_:
        return filename + "?" + URLEncoder.urlencode_vars(vars_)
    return filename
