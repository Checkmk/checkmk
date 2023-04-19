#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is our home-grown version of flask.globals and flask.ctx. It
# can be removed when fully do things the flasky way.

from __future__ import annotations

from werkzeug.local import LocalStack

_sentinel = object()


class _AppCtxGlobals:
    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def pop(self, name, default=_sentinel):
        if default is _sentinel:
            return self.__dict__.pop(name)
        return self.__dict__.pop(name, default)

    def setdefault(self, name, default=None):
        return self.__dict__.setdefault(name, default)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)


class AppContext:
    """Application state handling during a request

    The application context keeps track of the application-level data during a request, CLI
    command, or other activity. Rather than passing the application around to each function, the
    current_app and g proxies are accessed instead.

    This is similar to the The Request Context, which keeps track of request-level data during a
    request. A corresponding application context is pushed when a request context is pushed.

    The application context is a good place to store common data during a request or CLI command.

    See:

        https://flask.palletsprojects.com/en/1.1.x/appcontext/
        https://flask.palletsprojects.com/en/1.1.x/reqcontext/
    """

    def __init__(self, app, *, stack: LocalStack) -> None:  # type:ignore[no-untyped-def]
        self.app = app
        self.g = _AppCtxGlobals()
        self._stack = stack

    def __enter__(self) -> AppContext:
        self._stack.push(self)
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stack.pop()


def _call_hook(name: str) -> None:
    from cmk.gui import hooks

    hooks.call(name)
