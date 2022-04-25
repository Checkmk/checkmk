#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import partial
from typing import Any

from werkzeug.local import LocalProxy, LocalStack

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
