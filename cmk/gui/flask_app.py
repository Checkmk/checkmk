#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from flask import Flask

from cmk.gui import http
from cmk.gui.session import FileBasedSession


class CheckmkFlaskApp(Flask):
    request_class = http.Request
    response_class = http.Response
    session_interface = FileBasedSession()
