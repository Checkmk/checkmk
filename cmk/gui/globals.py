#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
from functools import partial
from typing import Any, TYPE_CHECKING

from werkzeug.local import LocalProxy, LocalStack

#####################################################################
# a namespace for storing data during an application context

if TYPE_CHECKING:
    # Import cycles
    from cmk.gui import htmllib, http, userdb
    from cmk.gui.config import Config
    from cmk.gui.context import RequestContext
    from cmk.gui.display_options import DisplayOptions
    from cmk.gui.plugins.openapi.restful_objects import Endpoint
    from cmk.gui.utils.logged_in import LoggedInUser
    from cmk.gui.utils.output_funnel import OutputFunnel
    from cmk.gui.utils.theme import Theme
    from cmk.gui.utils.timeout_manager import TimeoutManager
    from cmk.gui.utils.transaction_manager import TransactionManager
    from cmk.gui.utils.user_errors import UserErrors

#####################################################################
# application context

_app_ctx_stack = LocalStack()


def app_stack() -> LocalStack:
    return _app_ctx_stack


def _lookup_app_object(name):
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError("Working outside of application context.")
    return getattr(top, name)


current_app = LocalProxy(partial(_lookup_app_object, "app"))
g: Any = LocalProxy(partial(_lookup_app_object, "g"))


_request_ctx_stack = LocalStack()


def request_stack() -> LocalStack:
    return _request_ctx_stack


# NOTE: Flask offers the proxies below, and we should go into that direction,
# too. But currently our html class is a swiss army knife with tons of
# responsibilities which we should really, really split up...
def request_local_attr(name=None):
    """Delegate access to the corresponding attribute on RequestContext

    When the returned object is accessed, the Proxy will fetch the current
    RequestContext from the LocalStack and return the attribute given by `name`.

    Args:
        name (str): The name of the attribute on RequestContext

    Returns:
        A proxy which wraps the value stored on RequestContext.

    """
    return LocalProxy(partial(_lookup_req_object, name))


def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError("Working outside of request context.")

    if name is None:
        return top

    return getattr(top, name)


######################################################################
# TODO: This should live somewhere else...
class PrependURLFilter(logging.Filter):
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            record.msg = "%s %s" % (request.requested_url, record.msg)
        return True


# NOTE: All types FOO below are actually a Union[Foo, LocalProxy], but
# LocalProxy is meant as a transparent proxy, so we leave it out to de-confuse
# mypy. LocalProxy uses a lot of reflection magic, which can't be understood by
# tools in general.

local: RequestContext = request_local_attr()  # None as name will get the whole object.
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
