#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.web.context import RequestProtocol, ResponseProtocol


def set_language_cookie(request: RequestProtocol, response: ResponseProtocol, lang: str) -> None:
    cookie_lang = request.cookie("language")
    if cookie_lang == lang:
        return
    response.set_http_cookie("language", lang, secure=request.is_secure)
