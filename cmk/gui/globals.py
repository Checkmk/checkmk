#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
from functools import partial
from typing import Any, TYPE_CHECKING

from werkzeug.local import LocalProxy

from cmk.gui.ctx_stack import _lookup_app_object, request_local_attr

#####################################################################
# a namespace for storing data during an application context

if TYPE_CHECKING:
    # Import cycles
    from cmk.gui import htmllib, http, userdb
    from cmk.gui.config import Config
    from cmk.gui.display_options import DisplayOptions
    from cmk.gui.plugins.openapi.restful_objects import Endpoint
    from cmk.gui.utils.logged_in import LoggedInUser
    from cmk.gui.utils.output_funnel import OutputFunnel
    from cmk.gui.utils.theme import Theme
    from cmk.gui.utils.timeout_manager import TimeoutManager
    from cmk.gui.utils.transaction_manager import TransactionManager
    from cmk.gui.utils.user_errors import UserErrors


######################################################################
# TODO: This should live somewhere else...
class PrependURLFilter(logging.Filter):
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            record.msg = "%s %s" % (request.requested_url, record.msg)
        return True


# From app context
current_app = LocalProxy(partial(_lookup_app_object, "app"))
g: Any = LocalProxy(partial(_lookup_app_object, "g"))


# NOTE: All types FOO below are actually a Union[Foo, LocalProxy], but
# LocalProxy is meant as a transparent proxy, so we leave it out to de-confuse
# mypy. LocalProxy uses a lot of reflection magic, which can't be understood by
# tools in general.

# From request context
user: LoggedInUser = request_local_attr("user")
request: http.Request = request_local_attr("request")
response: http.Response = request_local_attr("response")
output_funnel: OutputFunnel = request_local_attr("output_funnel")
config: Config = request_local_attr("config")
session: userdb.Session = request_local_attr("session")
endpoint: Endpoint = request_local_attr("endpoint")
user_errors: UserErrors = request_local_attr("user_errors")

html: htmllib.html = request_local_attr("html")
timeout_manager: TimeoutManager = request_local_attr("timeout_manager")
theme: Theme = request_local_attr("theme")
transactions: TransactionManager = request_local_attr("transactions")
display_options: DisplayOptions = request_local_attr("display_options")
